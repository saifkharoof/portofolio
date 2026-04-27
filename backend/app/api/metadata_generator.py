from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from loguru import logger

from app.core.config import settings
from app.core.limiter import limiter
from app.core.deps import get_current_user
from app.models.admin import AdminUser
from app.services.metadata_service import metadata_service

router = APIRouter()

@router.post("/analyze", summary="Analyze an image and generate metadata using Gemini")
@limiter.limit(settings.rate_limit_admin)
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    _admin: AdminUser = Depends(get_current_user),
):
    """Accepts an uploaded image and returns AI-generated title, description, category, tags, and rating."""
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Could not read the uploaded file.")

    # Call the singleton service, utilizing its native retry & degradation features.
    result = await metadata_service.analyze_image(
        file_bytes=file_bytes, 
        mime_type=file.content_type,
        filename=file.filename
    )
    
    return result
