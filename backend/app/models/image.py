from typing import Optional
from app.models.base import BaseDocument
from pydantic import Field

class Image(BaseDocument):
    title: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    image_key: str = Field(...)
    category: str = Field(...)
    tags: Optional[list[str]] = Field(default_factory=list)
    rating: int = Field(default=0, ge=0, le=5)

    class Settings:
        name = "images"