import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger

from app.core.config import settings
from app.models.image import Image
from app.services.zilliz_service import zilliz_service
from app.services.metadata_service import metadata_service
from app.services.storage import storage

async def run_backfill():
    logger.info("Initializing DB connection...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(database=client[settings.database_name], document_models=[Image])
    
    if not zilliz_service.connect():
        logger.error("Failed to connect to Zilliz Cloud. Aborting backfill.")
        return

    logger.info("Fetching existing images from MongoDB...")
    images = await Image.find(Image.is_deleted == False).to_list()
    
    logger.info(f"Found {len(images)} images to sync to Zilliz.")
    
    for idx, image in enumerate(images):
        logger.info(f"Syncing ({idx+1}/{len(images)}): {image.title}")
        text_to_embed = f"Title: {image.title}. Category: {image.category}. Tags: {', '.join(image.tags)}. Description: {image.description or ''}"
        
        # Download image bytes from R2
        file_bytes = storage.get_file(image.image_key)
        mime_type = "image/jpeg"
        if image.image_key.endswith('.png'):
            mime_type = "image/png"
        elif image.image_key.endswith('.webp'):
            mime_type = "image/webp"
            
        # Generate multimodal embedding
        embedding = await metadata_service.embed_multimodal(text_to_embed, file_bytes, mime_type)
        
        # Construct URL
        img_url = f"{settings.r2_public_url}/{image.image_key}" if settings.r2_public_url else image.image_key
        
        # Upsert
        zilliz_service.upsert_image(
            image_id=str(image.id),
            title=image.title,
            category=image.category,
            tags=image.tags,
            image_url=img_url,
            text=text_to_embed,
            embedding=embedding
        )
        
        # Avoid hitting API rate limits if there are many images
        await asyncio.sleep(0.5)

    logger.success("Backfill complete!")

if __name__ == "__main__":
    asyncio.run(run_backfill())
