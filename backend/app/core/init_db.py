from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.models.admin import AdminUser
from app.models.image import Image
from app.core.config import settings


from loguru import logger

async def init_db():
    client = AsyncIOMotorClient(settings.mongodb_url)

    await init_beanie(
        database=client[settings.database_name],
        document_models=[Image, AdminUser]
    )
    logger.success("Successfully bootstrapped and connected to MongoDB clusters natively.")