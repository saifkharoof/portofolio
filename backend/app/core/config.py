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
    gemini_model_name: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    
    # MCP Server
    mcp_server_url: str = "http://127.0.0.1:8010/sse"
    mcp_api_token: str = ""

    # Chat — concurrency & validation
    chat_max_concurrent: int = 3
    chat_max_image_size_mb: int = 5
    chat_max_message_length: int = 2000
    
    # Zilliz Cloud / Milvus Vector Database
    zilliz_cloud_uri: Optional[str] = None
    zilliz_cloud_token: Optional[str] = None

    # Environment
    environment: str = "development"  # "development" or "production"

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"


settings = Settings()