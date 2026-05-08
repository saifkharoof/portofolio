"""Pydantic models for the Chat SSE stream protocol."""

from typing import List, Literal
from pydantic import BaseModel, field_validator


class PortfolioImage(BaseModel):
    """A single image result from the MCP vector search tool."""

    title: str = ""
    category: str = ""
    tags: List[str] = []
    image_url: str = ""
    description: str = ""
    relevance_score: float = 0.0

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v):
        """Accept a comma-separated string OR a list; always return a list."""
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        if isinstance(v, list):
            return v
        return []


# ---------------------------------------------------------------------------
# SSE event envelopes
# ---------------------------------------------------------------------------

class SSEContent(BaseModel):
    type: Literal["content"]
    text: str


class SSEToolStart(BaseModel):
    type: Literal["tool_start"]
    name: str


class SSEToolEnd(BaseModel):
    type: Literal["tool_end"]
    name: str
    images: List[PortfolioImage] = []


class SSEDone(BaseModel):
    type: Literal["done"]


class SSEError(BaseModel):
    type: Literal["error"]
    detail: str


class SSEBusy(BaseModel):
    """Sent when the concurrency limit is reached."""
    type: Literal["busy"]
    detail: str = "The assistant is currently busy. Please try again in a moment."
