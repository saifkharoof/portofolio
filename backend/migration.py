import asyncio
from app.core.init_db import init_db
from app.models.image import Image

async def patch():
    await init_db()
    images = await Image.find().to_list()
    for img in images:
        if not hasattr(img, "is_deleted"):
            await img.set({"is_deleted": False})
    print("Patched!")

if __name__ == "__main__":
    asyncio.run(patch())
