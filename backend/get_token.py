import asyncio
from app.core.init_db import init_db
from app.models.admin import AdminUser
from app.core.security import get_password_hash, create_access_token

async def get_test_token():
    await init_db()
    # Create or get an admin user
    user = await AdminUser.find_one(AdminUser.username == "tester")
    if not user:
        hashed_pw = get_password_hash("testpass")
        user = AdminUser(username="tester", hashed_password=hashed_pw)
        await user.insert()
    
    # Generate token
    token = create_access_token(data={"sub": user.username})
    print(token)

if __name__ == "__main__":
    asyncio.run(get_test_token())
