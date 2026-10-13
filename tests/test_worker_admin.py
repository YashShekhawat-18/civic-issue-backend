import pytest
from bson import ObjectId
from phase1011_support import (  # noqa: F401
    ADMIN_URL,
    audit_entries,
    clean_phase1011,
    department_id,
    make_admin,
    user_by_email,
)
from phase67_support import WORKER_URL, clean_notifications, make_complaint, make_worker, seeded, set_status  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

WORKERS = f"{ADMIN_URL}/workers"
PASSWORD = "Passw0rd123"


def worker_body(sync_db, **changes):
    body = {"name": "Ravi Kumar", "email": "Ravi@Example.com", "password": PASSWORD, "phone": "9876543210",
            "departmentId": department_id(sync_db, "ROAD")}
    body.update(changes)
    return body


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_admin_creates_a_worker_who_can_log_in_and_use_the_portal(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)

    response = client.post(WORKERS, json=worker_body(sync_db), headers=admin)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == "WORKER" and data["email"] == "ravi@example.com"  # e-mail is lower-cased
    assert data["department"]["code"] == "ROAD" and data["isActive"] is True
    assert "passwordHash" not in str(data) and PASSWORD not in str(data)
    assert user_by_email(sync_db, "ravi@example.com")["passwordHash"] != PASSWORD  # stored hashed

    token = login(client, "ravi@example.com").json()["data"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    items = client.get(WORKER_URL, headers=headers).json()["data"]["items"]
    assert [i["id"] for i in items] == [complaint_id]
    assert set_status(client, headers, complaint_id, "IN_PROGRESS").status_code == 200
    assert audit_entries(sync_db, "WORKER_CREATED")[0]["metadata"]["departmentCode"] == "ROAD"


@pytest.mark.parametrize("changes", [
    {"password": "short1"},                    # too short
    {"password": "onlyletters"},               # no digit
    {"password": "12345678"},                  # no letter
    {"email": "not-an-email"},
    {"name": "R"},
    {"phone": "abc"},
    {"role": "ADMIN"},                         # role can never be chosen
    {"isActive": False},                       # not allowed on create
])
def test_worker_validation(client, create_user, sync_db, changes):
    admin = make_admin(create_user)
    response = client.post(WORKERS, json=worker_body(sync_db, **changes), headers=admin)
    assert response.status_code == 422
    assert sync_db["users"].count_documents({"role": "WORKER"}) == 0


def test_worker_creation_rules(client, create_user, sync_db):
    admin = make_admin(create_user)
    assert client.post(WORKERS, json=worker_body(sync_db, departmentId=str(ObjectId())), headers=admin).status_code == 404
    assert client.post(WORKERS, json=worker_body(sync_db, departmentId="bad"), headers=admin).status_code == 400
    body = {k: v for k, v in worker_body(sync_db).items() if k != "departmentId"}
    assert client.post(WORKERS, json=body, headers=admin).status_code == 422

    assert client.post(WORKERS, json=worker_body(sync_db), headers=admin).status_code == 201
    assert client.post(WORKERS, json=worker_body(sync_db), headers=admin).status_code == 409  # same e-mail
    create_user(email="taken@example.com")
    assert client.post(WORKERS, json=worker_body(sync_db, email="taken@example.com"), headers=admin).status_code == 409

    sync_db["departments"].update_one({"code": "GARDEN"}, {"$set": {"isActive": False}})
    assert client.post(WORKERS, json=worker_body(sync_db, email="g@example.com", departmentId=department_id(sync_db, "GARDEN")), headers=admin).status_code == 404


def test_list_and_get_workers_show_only_workers(client, create_user, sync_db):
    admin = make_admin(create_user)
    create_user(email="citizen@example.com")
    make_worker(create_user, sync_db, "road1@example.com", "ROAD")
    make_worker(create_user, sync_db, "road2@example.com", "ROAD")
    make_worker(create_user, sync_db, "garden@example.com", "GARDEN")
    sync_db["users"].update_one({"email": "road2@example.com"}, {"$set": {"isActive": False}})

    def emails(query=""):
        return {w["email"] for w in client.get(f"{WORKERS}{query}", headers=admin).json()["data"]["items"]}

    assert emails() == {"road1@example.com", "road2@example.com", "garden@example.com"}  # no citizen, no admin
    assert emails(f"?departmentId={department_id(sync_db, 'ROAD')}") == {"road1@example.com", "road2@example.com"}
    assert emails("?isActive=true") == {"road1@example.com", "garden@example.com"}
    assert emails("?isActive=false") == {"road2@example.com"}
    assert client.get(f"{WORKERS}?departmentId=bad", headers=admin).status_code == 400
    page = client.get(f"{WORKERS}?limit=2&page=2", headers=admin).json()["data"]
    assert page["total"] == 3 and len(page["items"]) == 1

    worker_id = str(user_by_email(sync_db, "road1@example.com")["_id"])
    assert client.get(f"{WORKERS}/{worker_id}", headers=admin).json()["data"]["department"]["code"] == "ROAD"
    citizen_id = str(user_by_email(sync_db, "citizen@example.com")["_id"])
    admin_id = str(user_by_email(sync_db, "admin@example.com")["_id"])
    for not_a_worker in (citizen_id, admin_id, str(ObjectId())):
        assert client.get(f"{WORKERS}/{not_a_worker}", headers=admin).status_code == 404
        assert client.patch(f"{WORKERS}/{not_a_worker}", json={"name": "Hacker"}, headers=admin).status_code == 404
        assert client.delete(f"{WORKERS}/{not_a_worker}", headers=admin).status_code == 404
    assert user_by_email(sync_db, "citizen@example.com")["isActive"] is True


def test_admin_edits_and_moves_a_worker(client, create_user, sync_db):
    admin = make_admin(create_user)
    make_worker(create_user, sync_db, "road@example.com", "ROAD")
    worker_id = str(user_by_email(sync_db, "road@example.com")["_id"])
    url = f"{WORKERS}/{worker_id}"

    response = client.patch(url, json={"name": "New Name", "phone": "9123456789", "departmentId": department_id(sync_db, "GARDEN")}, headers=admin)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "New Name" and data["phone"] == "9123456789" and data["department"]["code"] == "GARDEN"
    assert client.patch(url, json={"phone": None}, headers=admin).json()["data"]["phone"] is None
    assert audit_entries(sync_db, "WORKER_UPDATED")[0]["metadata"]["fields"] == ["departmentId", "name", "phone"]

    assert client.patch(url, json={}, headers=admin).status_code == 422
    assert client.patch(url, json={"role": "ADMIN"}, headers=admin).status_code == 422
    assert client.patch(url, json={"email": "other@example.com"}, headers=admin).status_code == 422  # e-mail cannot change
    assert client.patch(url, json={"departmentId": str(ObjectId())}, headers=admin).status_code == 404
    assert user_by_email(sync_db, "road@example.com")["role"] == "WORKER"


def test_deactivated_worker_is_locked_out_and_can_return(client, create_user, sync_db):
    admin = make_admin(create_user)
    created = client.post(WORKERS, json=worker_body(sync_db), headers=admin).json()["data"]
    token = login(client, "ravi@example.com").json()["data"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get(WORKER_URL, headers=headers).status_code == 200

    response = client.delete(f"{WORKERS}/{created['id']}", headers=admin)
    assert response.status_code == 200 and response.json()["data"]["isActive"] is False
    assert client.get(WORKER_URL, headers=headers).status_code == 401           # the old token stops working
    assert login(client, "ravi@example.com").status_code == 403                 # and so does logging in
    assert audit_entries(sync_db, "WORKER_DEACTIVATED")
    assert sync_db["users"].count_documents({"email": "ravi@example.com"}) == 1  # account is kept

    assert client.patch(f"{WORKERS}/{created['id']}", json={"isActive": True}, headers=admin).status_code == 200
    assert login(client, "ravi@example.com").status_code == 200


def test_admin_can_reset_a_workers_password(client, create_user, sync_db):
    admin = make_admin(create_user)
    created = client.post(WORKERS, json=worker_body(sync_db), headers=admin).json()["data"]
    url = f"{WORKERS}/{created['id']}"
    assert client.patch(url, json={"password": "weak"}, headers=admin).status_code == 422

    response = client.patch(url, json={"password": "NewPassw0rd9"}, headers=admin)
    assert response.status_code == 200
    assert "passwordHash" not in response.text and "NewPassw0rd9" not in response.text
    assert login(client, "ravi@example.com", PASSWORD).status_code == 401
    assert login(client, "ravi@example.com", "NewPassw0rd9").status_code == 200
    assert audit_entries(sync_db, "WORKER_UPDATED")[0]["metadata"]["passwordReset"] is True


def test_worker_management_is_admin_only(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    worker_id = str(user_by_email(sync_db, "worker@example.com")["_id"])
    requests = [
        ("post", WORKERS, worker_body(sync_db)),
        ("get", WORKERS, None),
        ("get", f"{WORKERS}/{worker_id}", None),
        ("patch", f"{WORKERS}/{worker_id}", {"name": "Hacked"}),
        ("delete", f"{WORKERS}/{worker_id}", None),
    ]
    for method, url, body in requests:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(url, **kwargs).status_code == 401
        for headers in (citizen, worker):
            assert getattr(client, method)(url, headers=headers, **kwargs).status_code == 403
    assert user_by_email(sync_db, "worker@example.com")["isActive"] is True
