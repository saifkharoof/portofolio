"""
PortfolioMCP — MCP Server for Saif's Photography Portfolio.

Exposes tools and prompts over Streamable HTTP transport, guarded by
NVIDIA NeMo Guardrails and backed by a Milvus/Zilliz hybrid search index.
"""

import os
from typing import Sequence, Union
from loguru import logger

# Apply third-party patches BEFORE any other imports that touch these libraries
import app.core.patches  # noqa: F401  — side-effect import

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastmcp import FastMCP

from nemoguardrails import RailsConfig, LLMRails
from nemoguardrails.rails.llm.options import RailStatus

from app.core.config import settings
from app.tools.search import search_portfolio_images
from app.tools.prompt import get_portfolio_context

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("PortfolioMCP")


# ---------------------------------------------------------------------------
# Guardrails — initialised lazily inside the lifespan
# ---------------------------------------------------------------------------
guardrails: LLMRails | None = None


def _gemini_safe_is_content_safe(response) -> Sequence[Union[bool, str]]:
    """
    Drop-in replacement for NeMo's built-in `is_content_safe` output parser.

    Gemini (via langchain-google-genai) can return a list of content parts
    instead of a plain string. This wrapper normalises the response to a string
    before delegating to the original logic, preventing the
    `'list' object has no attribute 'strip'` crash.

    Safety philosophy: if the response cannot be parsed at all, we treat it as
    SAFE (fail-open) to avoid false positives in the RAG pipeline.
    """
    from nemoguardrails.llm.output_parsers import is_content_safe as _original

    # Log the raw response type and value for debugging
    logger.debug(f"is_content_safe raw response type={type(response).__name__!r} value={response!r}")

    # Coerce list/tuple responses (Gemini multi-part) to a single string
    if isinstance(response, (list, tuple)):
        parts = []
        for part in response:
            if hasattr(part, "text"):          # LangChain AIMessage content parts
                parts.append(part.text)
            elif isinstance(part, dict):
                parts.append(part.get("text") or part.get("content") or "")
            else:
                parts.append(str(part))
        response = " ".join(parts).strip()

    if not isinstance(response, str):
        response = str(response)

    try:
        return _original(response)
    except Exception:
        # Fail-open: if the parser itself throws, treat as SAFE
        logger.warning("is_content_safe parser raised unexpectedly — treating as safe (fail-open)")
        return [True]


async def _check_guardrails(query: str) -> str | None:
    """
    Run NeMo input rails on the query.

    Fail-open design: if the guardrail check raises ANY exception, the query
    is allowed through to avoid false positives in the RAG pipeline.

    Returns a blocked message string only when the rail explicitly blocks;
    returns None to allow the query through in all other cases.
    """
    if not guardrails:
        return None

    try:
        result = await guardrails.check_async(
            messages=[{"role": "user", "content": query}]
        )
        if result.status == RailStatus.BLOCKED:
            logger.warning(f"Guardrail BLOCKED query: {query!r} (rail: {result.rail})")
            return "I'm unable to process that request as it violates safety guidelines."
        # PASSED or MODIFIED — allow through
        logger.debug(f"Guardrail check passed for query: {query!r} (status: {result.status})")
    except Exception as e:
        # Fail-open: log and allow the query through rather than causing a false positive
        logger.warning(
            f"Guardrail check failed — allowing query through to avoid false positive. "
            f"Query: {query!r} | Error: {e}"
        )

    return None


# ---------------------------------------------------------------------------
# MCP Tool — Portfolio Search
# ---------------------------------------------------------------------------
@mcp.tool()
async def search_portfolio(query: str) -> str:
    """
    Search for images in the photography portfolio using semantic understanding.
    Returns a list of matching images and their URLs.
    """
    blocked = await _check_guardrails(query)
    if blocked:
        return blocked

    return search_portfolio_images(query)


# ---------------------------------------------------------------------------
# MCP Prompt — Base Persona
# ---------------------------------------------------------------------------
@mcp.prompt
def fetch_base_prompt() -> str:
    """
    Retrieves the base persona prompt and Saif's parsed PDF CV context from R2.
    Call this at the beginning of interactions to understand the agent's identity.
    """
    return get_portfolio_context()


# ---------------------------------------------------------------------------
# ASGI Application — FastAPI wrapper with lifespan
# ---------------------------------------------------------------------------
mcp_app = mcp.http_app()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Server-level startup / shutdown lifecycle."""
    global guardrails

    # --- Startup -----------------------------------------------------------
    logger.info("MCP Server starting up…")

    # 1) Set the Gemini key for NeMo Guardrails (reads from env)
    os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key or ""

    # 2) Initialise NeMo Guardrails
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "app", "core", "guardrails"
        )
        config = RailsConfig.from_path(config_path)
        # Override the LLM model from settings so config.yml doesn't drift
        if config.models and settings.gemini_model_name:
            config.models[0].model = settings.gemini_model_name
            logger.info(f"Guardrails model overridden to: {settings.gemini_model_name}")
        guardrails = LLMRails(config)
        # Register our Gemini-compatible parser that coerces list responses to str
        guardrails.register_output_parser(
            _gemini_safe_is_content_safe, name="is_content_safe"
        )
        logger.info("NeMo Guardrails initialised successfully.")
    except Exception as e:
        logger.error(f"Failed to load NeMo Guardrails config: {e}")
        guardrails = None

    # 3) Vector DB is initialised on import (app.services.vector_db)
    #    Just log its status.
    from app.services.vector_db import vector_db
    if vector_db.vector_store:
        logger.info("Milvus/Zilliz vector store is ready.")
    else:
        logger.warning("Milvus/Zilliz vector store is NOT available.")

    logger.info(f"MCP Server ready on port {settings.mcp_port}.")

    # 4) Forward lifespan to the MCP sub-app so its session manager initialises
    async with mcp_app.lifespan(application):
        yield

    # --- Shutdown ----------------------------------------------------------
    logger.info("MCP Server shutting down…")


# Mount FastMCP as a sub-application at root (FastMCP puts its endpoint at /mcp)
app = FastAPI(lifespan=lifespan)
app.mount("/", mcp_app)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting MCP Server via uvicorn (HTTP Transport)")
    uvicorn.run("main:app", host="0.0.0.0", port=settings.mcp_port, reload=True)
