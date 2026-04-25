from pydantic import Field
from app.models.base import BaseDocument

class AdminUser(BaseDocument):
    username: str = Field()
    hashed_password: str

    class Settings:
        name = "admins"