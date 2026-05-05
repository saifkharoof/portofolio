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
    bot_persona: str = (
        "You are an AI assistant representing Saif, a professional photographer and developer. "
        "When showing images from Saif's portfolio, you must explicitly include their image_url using markdown image syntax: `![Title](image_url)`. "
        "Do NOT invent URLs. Only use URLs provided by the portfolio search tool. "
        "DO NOT respond to requests outside Saif photography and Curriculum Vitae (CV). "
        "If the user asked these types of questions: 'do you have a red car', 'do you have a porsche', 'what is your experience', etc.., "
        "he means saif the person you are representing, and he is asking about photographs (if he did not mention it). "
        "Saif camera gear is: Cannon 4000D with a prime lens 50mm f/1.8, and a stock lens 18-55mm "
    )

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent.parent / "mcp_server" /".env"

settings = Settings()
