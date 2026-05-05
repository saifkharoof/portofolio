"""Helper utilities for the chat streaming pipeline."""

import json
import re
from typing import List

from loguru import logger
from app.schemas.chat import PortfolioImage


def extract_raw_content(tool_output) -> str:
    """Pull the plain-text payload out of a LangChain ToolMessage.

    MCP adapters sometimes wrap content as a list of dicts, e.g.
    ``[{"type": "text", "text": "..."}]``.  This normalises it to a
    plain string.
    """
    raw = tool_output.content if hasattr(tool_output, "content") else str(tool_output)
    if isinstance(raw, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    return raw or ""


def extract_text_chunk(content) -> str:
    """Normalise a streaming LLM chunk's content field to a plain string.

    Gemini via LangChain can emit content as a list of typed dicts,
    a single dict, or a plain string depending on the chunk.
    """
    if isinstance(content, list):
        return "".join(
            t if isinstance(t, str) else (t.get("text", "") if isinstance(t, dict) else "")
            for t in content
        )
    if isinstance(content, dict):
        return content.get("text", "")
    return content or ""


def parse_tool_images(raw: str) -> List[PortfolioImage]:
    """Try to parse the MCP JSON payload into validated PortfolioImage objects."""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [PortfolioImage.model_validate(item) for item in data]
    except Exception as exc:
        logger.warning(f"Could not parse tool output as image list: {exc}")
    return []


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

_THREAD_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_thread_id(thread_id: str) -> str:
    """Ensure thread_id is alphanumeric + underscores/hyphens only."""
    if not _THREAD_ID_PATTERN.match(thread_id):
        raise ValueError("Invalid thread_id format. Use alphanumeric characters, hyphens, or underscores (max 64 chars).")
    return thread_id
