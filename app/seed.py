import asyncio

from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo, get_database
from app.core.security import hash_password
from app.models.badge import BADGES_COLLECTION, build_badge_document
from app.models.category import CATEGORIES_COLLECTION, build_category_document
from app.models.department import DEPARTMENTS_COLLECTION, build_department_document
from app.models.indexes import create_all_indexes
from app.models.user import USERS_COLLECTION, Role, build_user_document
from app.seed_data import BADGES, CATEGORIES, DEPARTMENTS, WORKERS


async def insert_if_missing(collection, key_field: str, document: dict) -> bool:
    """Insert only if no document with the same key exists. Returns True if inserted.

    $setOnInsert never changes an existing document, so edits made later by an admin
    survive running the seed again. The unique indexes make this safe against duplicates.
    """
    result = await collection.update_one(
        {key_field: document[key_field]},
        {"$setOnInsert": document},
        upsert=True,
    )
    return result.upserted_id is not None


def report(label: str, created: int, total: int) -> None:
    print(f"{label}: {created} created, {total - created} already existed")


async def seed_departments(db) -> dict:
    created = 0
    for item in DEPARTMENTS:
        document = build_department_document(**item)
        if await insert_if_missing(db[DEPARTMENTS_COLLECTION], "code", document):
            created += 1
    report("Departments", created, len(DEPARTMENTS))

    # Map department code -> its database id, needed to link categories and workers
    departments = await db[DEPARTMENTS_COLLECTION].find({}, {"code": 1}).to_list()
    return {department["code"]: department["_id"] for department in departments}


async def seed_categories(db, department_ids: dict) -> None:
    created = 0
    for item in CATEGORIES:
        document = build_category_document(
            name=item["name"],
            code=item["code"],
            description=item["description"],
            department_id=department_ids[item["departmentCode"]],
        )
        if await insert_if_missing(db[CATEGORIES_COLLECTION], "code", document):
            created += 1
    report("Categories", created, len(CATEGORIES))


async def seed_users(db, department_ids: dict) -> None:
    people = [
        {
            "name": settings.seed_admin_name,
            "email": settings.seed_admin_email.lower(),
            "password": settings.seed_admin_password,
            "role": Role.ADMIN,
            "department_id": None,
        }
    ]
    for worker in WORKERS:
        people.append(
            {
                "name": worker["name"],
                "email": worker["email"],
                "password": settings.seed_worker_password,
                "role": Role.WORKER,
                "department_id": department_ids[worker["departmentCode"]],
            }
        )

    users = db[USERS_COLLECTION]
    created = 0
    for person in people:
        existing = await users.find_one({"email": person["email"]}, {"role": 1})
        if existing:
            # We never change an existing account, even if its role is different
            if existing["role"] != person["role"].value:
                print(f"WARNING: {person['email']} already exists as {existing['role']}; left unchanged")
            continue

        document = build_user_document(
            name=person["name"],
            email=person["email"],
            password_hash=await hash_password(person["password"]),
            role=person["role"],
            department_id=person["department_id"],
        )
        try:
            await users.insert_one(document)
            created += 1
        except DuplicateKeyError:
            pass
    report("Users", created, len(people))


async def seed_badges(db) -> None:
    created = 0
    for item in BADGES:
        document = build_badge_document(
            name=item["name"],
            description=item["description"],
            icon=item["icon"],
            points_required=item["pointsRequired"],
        )
        if await insert_if_missing(db[BADGES_COLLECTION], "name", document):
            created += 1
    report("Badges", created, len(BADGES))


async def run_seed(db) -> None:
    await create_all_indexes(db)
    department_ids = await seed_departments(db)
    await seed_categories(db, department_ids)
    await seed_users(db, department_ids)
    await seed_badges(db)


def check_seed_settings() -> None:
    problems = []
    if not settings.seed_admin_email:
        problems.append("SEED_ADMIN_EMAIL is empty")
    if len(settings.seed_admin_password) < 8:
        problems.append("SEED_ADMIN_PASSWORD must be at least 8 characters")
    if len(settings.seed_worker_password) < 8:
        problems.append("SEED_WORKER_PASSWORD must be at least 8 characters")
    if problems:
        raise SystemExit("Cannot seed. Fix your .env file:\n- " + "\n- ".join(problems))


async def main() -> None:
    check_seed_settings()
    await connect_to_mongo()
    try:
        await run_seed(get_database())
    finally:
        await close_mongo_connection()
    print("Seeding finished")


if __name__ == "__main__":
    asyncio.run(main())