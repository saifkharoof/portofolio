"""
PortfolioMCP — MCP Server for Saif's Photography Portfolio.

Exposes tools and prompts over Streamable HTTP transport, backed by a Milvus/Zilliz hybrid search index.
"""

from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastmcp import FastMCP

from app.core.config import settings
from app.tools.search import search_portfolio_images
from app.tools.prompt import get_portfolio_context

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("PortfolioMCP")


from pydantic import Field

# ---------------------------------------------------------------------------
# MCP Tool — Portfolio Search
# ---------------------------------------------------------------------------
@mcp.tool()
async def search_portfolio(
    query: str = Field("", description="Text query to search the portfolio."),
) -> str:
    """
    Search for images in the photography portfolio using semantic understanding.
    Returns a list of matching images and their URLs.
    """
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
mcp_app = mcp.http_app(transport="sse")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Server-level startup / shutdown lifecycle."""
    # --- Startup -----------------------------------------------------------
    logger.info("MCP Server starting up…")

    # Vector DB is initialised on import (app.services.vector_db)
    # Just log its status.
    from app.services.vector_db import vector_db
    if vector_db.vector_store:
        logger.info("Milvus/Zilliz vector store is ready.")
    else:
        logger.warning("Milvus/Zilliz vector store is NOT available.")

    logger.info(f"MCP Server ready on port {settings.mcp_port}.")

    # Forward lifespan to the MCP sub-app so its session manager initialises
    async with mcp_app.lifespan(application):
        yield

    # --- Shutdown ----------------------------------------------------------
    logger.info("MCP Server shutting down…")


# Mount FastMCP as a sub-application at root (FastMCP puts its endpoint at /mcp)
app = FastAPI(lifespan=lifespan)
app.mount("/", mcp_app)

import uvicorn

logger.info("Starting MCP Server via uvicorn (HTTP Transport)")
uvicorn.run("main:app", host="0.0.0.0", port=settings.mcp_port, reload=True)


