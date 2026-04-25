from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.base import BaseResponse
from app.models.image import Image
from app.core.config import settings
from app.services.storage import storage

class ImageUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    rating: Optional[int] = Field(None, ge=0, le=5)

class ImageResponse(BaseResponse):
    title: str
    description: Optional[str] = None
    category: str
    image_url: str
    tags: list[str]
    rating: int

    @classmethod
    def from_doc(cls, doc: Image) -> "ImageResponse":
        if settings.r2_public_url:
            img_src = f"{settings.r2_public_url.rstrip('/')}/{doc.image_key}"
        else:
            img_src = storage.generate_presigned_url(doc.image_key)

        return cls(
            id=str(doc.id),
            title=doc.title,
            description=doc.description,
            category=doc.category,
            image_url=img_src,
            tags=doc.tags or [],
            rating=doc.rating,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
