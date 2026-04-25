import asyncio
import getpass
from app.core.init_db import init_db
from app.models.admin import AdminUser
from app.core.security import get_password_hash


async def create_superuser():
    print("Connecting to database...")
    # Initialize Beanie and connect to MongoDB
    await init_db()

    print("\n--- Create Admin Account ---")
    username = input("Enter new admin username: ")
    # getpass hides the password while you type it
    password = getpass.getpass("Enter new admin password: ")

    # Check if this username is already taken
    existing_user = await AdminUser.find_one(AdminUser.username == username)
    if existing_user:
        print(f"\n❌ Error: The user '{username}' already exists in the database.")
        return

    # Hash the password
    hashed_pw = get_password_hash(password)

    # Create the user document and save it to MongoDB
    admin_user = AdminUser(username=username, hashed_password=hashed_pw)
    await admin_user.insert()

    print(f"\n✅ Success! Admin user '{username}' created securely.")


if __name__ == "__main__":
    # Run the async function
    asyncio.run(create_superuser())