from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_url: str
    database_name: str
    secret_key: str
    access_token_expire_minutes: int = 60

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Cloudflare R2
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "images"
    r2_public_url: Optional[str] = None
    rate_limit_public: str = "60/minute"
    rate_limit_admin: str = "10/minute"

    # AI
    gemini_api_key: Optional[str] = None
    gemini_model_name: str = "gemini-3-flash-preview"

    # Environment
    environment: str = "development"  # "development" or "production"

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"


settings = Settings()