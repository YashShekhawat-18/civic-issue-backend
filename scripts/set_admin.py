"""Create an admin, or change an admin's email and/or password. Run from the backend folder:

  python scripts/set_admin.py

It asks questions (the password is not shown while you type). It only touches ADMIN accounts.
"""
import asyncio
import getpass
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import USERS_COLLECTION, Role, build_user_document  # noqa: E402

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def check_password(password):
    if len(password) < 8 or len(password) > 72:
        return "The password must be 8 to 72 characters"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "The password needs at least one letter and one number"
    return None


async def apply(db, *, old_email, new_email, password, name):
    users = db[USERS_COLLECTION]
    new_email = new_email.strip().lower()
    if not EMAIL_RE.match(new_email):
        raise ValueError("That is not a valid email address")
    if password is not None and (problem := check_password(password)):
        raise ValueError(problem)

    if old_email:
        old_email = old_email.strip().lower()
        admin = await users.find_one({"email": old_email})
        if admin is None:
            raise ValueError(f"No account with the email {old_email}")
        if admin["role"] != Role.ADMIN.value:
            raise ValueError(f"{old_email} is not an admin, so this script will not change it")
        changes = {}
        if new_email != old_email:
            if await users.find_one({"email": new_email}):
                raise ValueError(f"{new_email} is already used by another account")
            changes["email"] = new_email
        if password:
            changes["passwordHash"] = await hash_password(password)
        if name:
            changes["name"] = name
        if not changes:
            return "Nothing to change."
        changes["updatedAt"] = datetime.now(timezone.utc)
        changes["isActive"] = True
        await users.update_one({"_id": admin["_id"]}, {"$set": changes})
        return f"Admin updated. Log in with {new_email}."

    existing = await users.find_one({"email": new_email})
    if existing:
        if existing["role"] != Role.ADMIN.value:
            raise ValueError(f"{new_email} already belongs to a {existing['role'].lower()}. Use a different email")
        if not password:
            raise ValueError("That admin already exists. Enter a new password to reset it")
        await users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"passwordHash": await hash_password(password), "isActive": True, "updatedAt": datetime.now(timezone.utc)}},
        )
        return f"Password reset. Log in with {new_email}."
    if not password:
        raise ValueError("A new admin needs a password")
    await users.insert_one(
        build_user_document(name=name or "Admin", email=new_email, password_hash=await hash_password(password), role=Role.ADMIN)
    )
    return f"New admin created. Log in with {new_email}."


def ask(prompt, secret=False):
    return (getpass.getpass(prompt) if secret else input(prompt)).strip()


async def main():
    print("Admin setup. Press Enter to skip a question.\n")
    old = ask("Email of the EXISTING admin to change (empty = create a new admin): ") or None
    new = ask("Admin email to use from now on: ")
    name = ask("Name (optional): ") or None
    password = ask("Password (not shown, 8+ characters with a letter and a number): ", secret=True) or None
    if password and password != ask("Type the password again: ", secret=True):
        print("\nThe two passwords were different. Nothing was changed.")
        return 1
    await connect_to_mongo()
    try:
        print("\n" + await apply(get_database(), old_email=old, new_email=new, password=password, name=name))
        return 0
    except ValueError as err:
        print(f"\nNothing was changed. {err}.")
        return 1
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
