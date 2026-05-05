from fastapi import FastAPI, Request
from loguru import logger
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.images import router as images_router
from app.api.metadata_generator import router as ai_router
from app.api.chat import router as chat_router
from app.core.init_db import init_db
from app.core.config import settings
from app.services.mcp_client import mcp_service

# Swagger metadata
description = """
### Saif's Portfolio API

This is the backend powering my personal photography portfolio and admin dashboard.
It handles secure image uploads, database management, and JWT authentication.

#### Features
* **Authentication**: Secure admin login using JWT tokens.
* **Images**: CRUD operations for photography metadata.
* **Agentic Chat**: Multimodal LangGraph chat integrating with MCP vector search.
"""


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.core.limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Portfolio Backend...")
    await init_db()
    FastAPICache.init(InMemoryBackend(), prefix="portfolio-cache")
    
    # Initialize MCP connection for LangGraph Agent
    await mcp_service.connect()
    
    logger.success("Backend booted successfully.")
    yield
    logger.info("Shutting down.")
    await mcp_service.disconnect()


# Disable Swagger docs in production
is_prod = settings.environment == "production"

# Create the FastAPI application
app = FastAPI(
    title="Saif's Portfolio API",
    description=description,
    version="1.0.0",
    contact={
        "name": "Saif",
        "url": "https://github.com/saifkharoof",
    },
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )

# CORS — parse allowed origins from environment config
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Backend and Database are live!"}


# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(images_router, prefix="/api/images", tags=["Images"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Generation"])
app.include_router(chat_router, prefix="/api/chat", tags=["Agentic Chat"])