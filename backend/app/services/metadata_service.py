import json
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.metadata_schema import ImageAnalysisResult

class MetadataService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetadataService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.installed = True
        else:
            self.client = None
            self.installed = False
            logger.warning("Gemini API key not found. AI operations will gracefully degrade.")
            
        self._initialized = True

    async def analyze_image(self, file_bytes: bytes, mime_type: str, filename: str = "Unknown") -> Dict[str, Any]:
        """
        Analyzes an image to generate curated metadata.
        Implements Exponential Backoff for 503/429 errors and graceful degradation.
        """
        fallback_data = {
            "title": filename.rsplit('.', 1)[0].replace('_', ' ').title(),
            "description": "",
            "category": "nature",
            "tags": [],
            "rating": 0
        }

        if not self.installed:
            return fallback_data

        instruction = (
            "You are a professional photography curator. Analyze this photo and generate metadata. "
            "For the category field, choose exactly one of: 'nature' or 'cars'. "
            "For tags, provide 4-6 relevant single-word tags useful for search and SEO. "
            "For rating, evaluate the photo quality on a scale of 1-5 based on composition, lighting, and subject."
        )

        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=settings.gemini_model_name,
                    contents=[
                        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
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
                error_msg = str(e)
                logger.error(f"Gemini API Error (Attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                # Check if it's a temporary server error (503) or rate limit (429)
                if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 1s, 2s...
                        logger.info(f"Retrying AI analysis in {wait_time}s due to high demand...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                logger.error(f"AI Analysis completely failed. Returning fallback data for {filename}.")
                # If we exhausted retries or hit a hard error (e.g. 400 Bad Request), degrade gracefully.
                return fallback_data

    async def embed_multimodal(self, text: str, image_bytes: Optional[bytes] = None, mime_type: str = "image/jpeg") -> list[float]:
        """Generate a 768-dim embedding for Zilliz using Gemini, combining text and image if provided."""
        if not self.installed:
            return [0.0] * 768
            
        try:
            contents = []
            if image_bytes:
                contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            if text:
                contents.append(text)
                
            response = await self.client.aio.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=contents,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Error generating multimodal embedding: {e}")
            return [0.0] * 768

# Instantiate singleton
metadata_service = MetadataService()
