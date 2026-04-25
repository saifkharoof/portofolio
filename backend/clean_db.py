import asyncio
from app.core.init_db import init_db
from app.models.image import Image

async def clean():
    await init_db()
    # Find images that don't match our new schema or have dummy URLs
    images = await Image.find().to_list()
    for img in images:
        if "dummy-r2-url" in img.image_key or img.title in ["Test Image", "Golden Hour Sunset"]:
            await img.delete()

if __name__ == "__main__":
    asyncio.run(clean())
