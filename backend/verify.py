import asyncio
from app.core.init_db import init_db
from app.models.image import Image
from beanie import PydanticObjectId

async def check():
    await init_db()
    img = await Image.get(PydanticObjectId('69e4d51cd50c737ab3760840'))
    print('is_deleted flag in DB:', getattr(img, 'is_deleted', None))
    assert getattr(img, 'is_deleted', None) is True
    print("Test Validated!")

if __name__ == "__main__":
    asyncio.run(check())
