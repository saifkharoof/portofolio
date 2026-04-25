from datetime import datetime, timezone
from beanie import Document
from pydantic import Field

class BaseDocument(Document):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = Field(default=False)

    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        await super().save(*args, **kwargs)

    async def update(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        await super().update(*args, **kwargs)

    async def set(self, expression, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        if isinstance(expression, dict):
            expression["updated_at"] = self.updated_at
        await super().set(expression, **kwargs)
