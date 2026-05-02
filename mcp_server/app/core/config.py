import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Gemini AI
    gemini_api_key: Optional[str] = None
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_model_name: str = "gemini-3.1-flash-lite"
    
    # Zilliz / Milvus Vector Database
    zilliz_cloud_uri: Optional[str] = None
    zilliz_cloud_token: Optional[str] = None
    collection_name: str = "portfolio_images"

    # Cloudflare R2
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "portfolio-cv"
    
    # FastMCP
    mcp_transport: str = "sse" # "stdio" or "sse"
    mcp_port: int = 8010    
    # Persona configuration
    bot_persona: str = "You are an AI assistant representing Saif, a professional photographer and developer."

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent.parent / "mcp_server" /".env"

settings = Settings()
