from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from loguru import logger
from google import genai
from google.genai import types
import json

from app.core.config import settings
from app.core.limiter import limiter
from app.core.deps import get_current_user
from app.models.admin import AdminUser
from app.schemas.metadata_schema import ImageAnalysisResult

router = APIRouter()

@router.post("/analyze", summary="Analyze an image and generate metadata using Gemini")
@limiter.limit(settings.rate_limit_admin)
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    _admin: AdminUser = Depends(get_current_user),
):
    """Accepts an uploaded image and returns AI-generated title, description, category, tags, and rating."""
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not configured.")
        raise HTTPException(status_code=500, detail="AI analysis is not configured. Please set your Gemini API key.")
        
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Could not read the uploaded file.")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        
        instruction = (
            "You are a professional photography curator. Analyze this photo and generate metadata. "
            "For the category field, choose exactly one of: 'nature' or 'cars'. "
            "For tags, provide 4-6 relevant single-word tags useful for search and SEO. "
            "For rating, evaluate the photo quality on a scale of 1-5 based on composition, lighting, and subject."
        )
        
        response = client.models.generate_content(
            model=settings.gemini_model_name,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=file.content_type),
                instruction
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ImageAnalysisResult,
                temperature=0.3
            ),
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail="AI analysis failed. Please try again.")
