import pytest
from bson import ObjectId
from phase1011_support import (  # noqa: F401
    ADMIN_URL,
    audit_entries,
    category_id,
    clean_phase1011,
    department_id,
    make_admin,
)
from phase67_support import clean_notifications, make_complaint, make_worker, seeded  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

DEPARTMENTS = "/api/v1/departments"
CATEGORIES = "/api/v1/categories"


def new_department(code="PARKS", name="Parks"):
    return {"name": name, "code": code, "description": "Public parks"}


# ---------- departments ----------

def test_admin_creates_a_department(client, create_user, sync_db):
    admin = make_admin(create_user)
    response = client.post(DEPARTMENTS, json={"name": " Parks ", "code": "parks", "description": "Public parks"}, headers=admin)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Parks" and data["code"] == "PARKS" and data["isActive"] is True  # trimmed and upper-cased
    assert sync_db["departments"].count_documents({"code": "PARKS"}) == 1
    assert audit_entries(sync_db, "DEPARTMENT_CREATED")[0]["metadata"]["code"] == "PARKS"
    assert client.get(f"{DEPARTMENTS}/{data['id']}", headers=admin).json()["data"]["code"] == "PARKS"


@pytest.mark.parametrize("body", [
    {"name": "P", "code": "PARKS"},                      # name too short
    {"name": "Parks", "code": "bad code!"},              # invalid code
    {"name": "Parks", "code": "X"},                      # code too short
    {"name": "Parks"},                                   # code missing
    {"name": "Parks", "code": "PARKS", "isActive": False},  # not allowed on create
    {"name": "Parks", "code": "PARKS", "description": "x" * 301},
])
def test_department_validation(client, create_user, body):
    admin = make_admin(create_user)
    assert client.post(DEPARTMENTS, json=body, headers=admin).status_code == 422


def test_duplicate_department_name_or_code_is_409(client, create_user):
    admin = make_admin(create_user)
    assert client.post(DEPARTMENTS, json=new_department(), headers=admin).status_code == 201
    assert client.post(DEPARTMENTS, json=new_department(), headers=admin).status_code == 409
    assert client.post(DEPARTMENTS, json=new_department(code="OTHER_CODE"), headers=admin).status_code == 409  # same name
    assert client.post(DEPARTMENTS, json=new_department(name="Other Name"), headers=admin).status_code == 409  # same code


def test_admin_edits_a_department(client, create_user, sync_db):
    admin = make_admin(create_user)
    parks = client.post(DEPARTMENTS, json=new_department(), headers=admin).json()["data"]
    url = f"{DEPARTMENTS}/{parks['id']}"

    response = client.patch(url, json={"name": "Parks and Gardens", "description": "Updated"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Parks and Gardens"
    changes = audit_entries(sync_db, "DEPARTMENT_UPDATED")[0]["metadata"]["changes"]
    assert changes["name"] == ["Parks", "Parks and Gardens"]

    assert client.patch(url, json={}, headers=admin).status_code == 422
    assert client.patch(url, json={"name": "Road"}, headers=admin).status_code == 409  # taken by a seeded department
    assert client.patch(url, json={"colour": "red"}, headers=admin).status_code == 422
    assert client.patch(f"{DEPARTMENTS}/{ObjectId()}", json={"name": "Whatever"}, headers=admin).status_code == 404


def test_deactivating_a_department_follows_the_safety_rules(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    parks = client.post(DEPARTMENTS, json=new_department(), headers=admin).json()["data"]
    url = f"{DEPARTMENTS}/{parks['id']}"

    category = client.post(CATEGORIES, json={"name": "Park Damage", "code": "PARK_DAMAGE", "departmentId": parks["id"]}, headers=admin).json()["data"]
    assert client.delete(url, headers=admin).status_code == 409  # still has an active category
    client.delete(f"{CATEGORIES}/{category['id']}", headers=admin)

    worker = client.post(f"{ADMIN_URL}/workers", headers=admin, json={
        "name": "Park Worker", "email": "park@example.com", "password": "Passw0rd123", "departmentId": parks["id"]}).json()["data"]
    assert client.delete(url, headers=admin).status_code == 409  # still has an active worker
    client.delete(f"{ADMIN_URL}/workers/{worker['id']}", headers=admin)

    # a department with an open complaint cannot be switched off
    road_url = f"{DEPARTMENTS}/{department_id(sync_db, 'ROAD')}"
    make_complaint(client, citizen, sync_db, code="POTHOLE")
    sync_db["categories"].update_many({"departmentId": ObjectId(department_id(sync_db, "ROAD"))}, {"$set": {"isActive": False}})
    assert client.delete(road_url, headers=admin).status_code == 409

    response = client.delete(url, headers=admin)
    assert response.status_code == 200 and response.json()["data"]["isActive"] is False
    assert audit_entries(sync_db, "DEPARTMENT_DEACTIVATED")
    assert sync_db["departments"].count_documents({"code": "PARKS"}) == 1  # kept, not removed
    assert client.delete(url, headers=admin).status_code == 200            # repeating it is harmless
    assert len(audit_entries(sync_db, "DEPARTMENT_DEACTIVATED")) == 1


def test_inactive_department_is_hidden_from_users_but_not_from_admin(client, create_user):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    parks = client.post(DEPARTMENTS, json=new_department(), headers=admin).json()["data"]
    client.delete(f"{DEPARTMENTS}/{parks['id']}", headers=admin)

    public_codes = [d["code"] for d in client.get(DEPARTMENTS, headers=citizen).json()["data"]]
    assert "PARKS" not in public_codes
    assert client.get(f"{DEPARTMENTS}/{parks['id']}", headers=citizen).status_code == 404
    assert client.get(f"{DEPARTMENTS}/{parks['id']}", headers=admin).status_code == 200
    admin_codes = [d["code"] for d in client.get(f"{ADMIN_URL}/departments", headers=admin).json()["data"]]
    assert "PARKS" in admin_codes

    # switching it back on
    again = client.patch(f"{DEPARTMENTS}/{parks['id']}", json={"isActive": True}, headers=admin)
    assert again.status_code == 200 and again.json()["data"]["isActive"] is True
    assert "PARKS" in [d["code"] for d in client.get(DEPARTMENTS, headers=citizen).json()["data"]]


def test_citizens_and_workers_can_read_but_not_change_departments(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    for headers in (citizen, worker):
        assert client.post(DEPARTMENTS, json=new_department(), headers=headers).status_code == 403
    assert client.post(DEPARTMENTS, json=new_department()).status_code == 401


# ---------- categories ----------

def test_admin_creates_edits_and_deactivates_a_category(client, create_user, sync_db):
    admin = make_admin(create_user)
    body = {"name": "Broken Bench", "code": "broken_bench", "description": "Park benches", "departmentId": department_id(sync_db, "GARDEN")}
    response = client.post(CATEGORIES, json=body, headers=admin)
    assert response.status_code == 201
    created = response.json()["data"]
    assert created["code"] == "BROKEN_BENCH" and created["department"]["code"] == "GARDEN"
    url = f"{CATEGORIES}/{created['id']}"
    assert audit_entries(sync_db, "CATEGORY_CREATED")

    moved = client.patch(url, json={"departmentId": department_id(sync_db, "ROAD"), "name": "Broken Bench Road"}, headers=admin)
    assert moved.status_code == 200 and moved.json()["data"]["department"]["code"] == "ROAD"
    assert audit_entries(sync_db, "CATEGORY_UPDATED")

    assert client.delete(url, headers=admin).json()["data"]["isActive"] is False
    assert audit_entries(sync_db, "CATEGORY_DEACTIVATED")
    assert "BROKEN_BENCH" not in [c["code"] for c in client.get(CATEGORIES, headers=admin).json()["data"]]
    assert "BROKEN_BENCH" in [c["code"] for c in client.get(f"{ADMIN_URL}/categories", headers=admin).json()["data"]]

    back = client.patch(url, json={"isActive": True}, headers=admin)
    assert back.status_code == 200 and back.json()["data"]["isActive"] is True


def test_category_rules(client, create_user, sync_db):
    admin = make_admin(create_user)
    good = {"name": "Broken Bench", "code": "BROKEN_BENCH", "departmentId": department_id(sync_db, "GARDEN")}
    assert client.post(CATEGORIES, json={**good, "departmentId": str(ObjectId())}, headers=admin).status_code == 404
    assert client.post(CATEGORIES, json={**good, "departmentId": "bad"}, headers=admin).status_code == 400
    assert client.post(CATEGORIES, json={**good, "code": "POTHOLE"}, headers=admin).status_code == 409  # code taken
    assert client.post(CATEGORIES, json={**good, "extra": 1}, headers=admin).status_code == 422
    assert client.post(CATEGORIES, json={"name": "x"}, headers=admin).status_code == 422
    assert client.patch(f"{CATEGORIES}/{category_id(sync_db)}", json={}, headers=admin).status_code == 422
    assert client.patch(f"{CATEGORIES}/{category_id(sync_db)}", json={"code": "GARBAGE"}, headers=admin).status_code == 409
    assert client.patch(f"{CATEGORIES}/{ObjectId()}", json={"name": "Nope"}, headers=admin).status_code == 404

    # a department must be active to receive a category
    parks = client.post(DEPARTMENTS, json=new_department(), headers=admin).json()["data"]
    client.delete(f"{DEPARTMENTS}/{parks['id']}", headers=admin)
    assert client.post(CATEGORIES, json={**good, "departmentId": parks["id"]}, headers=admin).status_code == 404


def test_category_cannot_be_switched_on_under_an_inactive_department(client, create_user, sync_db):
    admin = make_admin(create_user)
    parks = client.post(DEPARTMENTS, json=new_department(), headers=admin).json()["data"]
    category = client.post(CATEGORIES, json={"name": "Park Damage", "code": "PARK_DAMAGE", "departmentId": parks["id"]}, headers=admin).json()["data"]
    client.delete(f"{CATEGORIES}/{category['id']}", headers=admin)
    client.delete(f"{DEPARTMENTS}/{parks['id']}", headers=admin)
    assert client.patch(f"{CATEGORIES}/{category['id']}", json={"isActive": True}, headers=admin).status_code == 404


def test_a_new_category_can_be_used_for_a_complaint_and_follows_its_department(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    category = client.post(CATEGORIES, json={"name": "Broken Bench", "code": "BROKEN_BENCH", "departmentId": department_id(sync_db, "GARDEN")}, headers=admin).json()["data"]
    from civic_test_helpers import complaint_form, post_complaint

    form = complaint_form(sync_db, code="POTHOLE", categoryId=category["id"])
    response = post_complaint(client, citizen, form)
    assert response.status_code == 201
    assert response.json()["data"]["department"]["code"] == "GARDEN"


def test_deactivated_category_cannot_receive_new_complaints(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    client.delete(f"{CATEGORIES}/{category_id(sync_db, 'POTHOLE')}", headers=admin)
    from civic_test_helpers import complaint_form, post_complaint

    assert post_complaint(client, citizen, complaint_form(sync_db, code="POTHOLE")).status_code == 404


def test_category_changes_need_admin(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    url = f"{CATEGORIES}/{category_id(sync_db)}"
    body = {"name": "Hacked"}
    assert client.patch(url, json=body, headers=citizen).status_code == 403
    assert client.delete(url, headers=citizen).status_code == 403
    assert client.post(CATEGORIES, json={"name": "Nope", "code": "NOPE", "departmentId": department_id(sync_db)}, headers=citizen).status_code == 403
    assert client.patch(url, json=body).status_code == 401
    assert client.get(url, headers=citizen).status_code == 200  # reading is allowed for everyone logged in
