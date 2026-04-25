from pydantic import BaseModel, Field

class ImageAnalysisResult(BaseModel):
    title: str = Field(description="A concise, creative title for the photograph.")
    description: str = Field(description="A 1-2 sentence description of the scene, lighting, or subject.")
    category: str = Field(description="Exactly one of: 'nature' or 'cars'.")
    tags: list[str] = Field(description="4-6 relevant single-word tags for search and SEO.")
    rating: int = Field(description="Photo quality rating from 1 (poor) to 5 (excellent).", ge=1, le=5)
