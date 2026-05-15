import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from loguru import logger


class MCPService:
    def __init__(self, sse_url: str, api_token: str | None = None):
        self.sse_url = sse_url
        self.api_token = api_token
        self._async_exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self.tools = []

    async def connect(self):
        from app.core.config import settings
        logger.info(f"Connecting to MCP endpoint: {self.sse_url}")

        for attempt in range(5):
            try:
                if settings.environment == "production":
                    logger.info("Using streamablehttp_client for production (Perfect Horizon)")
                    headers = {"Accept": "application/json, text/event-stream"}
                    if self.api_token:
                        headers["Authorization"] = f"Bearer {self.api_token}"
                    client_context = streamablehttp_client(self.sse_url, headers=headers)
                    streams = await self._async_exit_stack.enter_async_context(client_context)
                    read_stream, write_stream = streams[0], streams[1]
                else:
                    logger.info("Using sse_client for local development")
                    client_context = sse_client(self.sse_url)
                    read_stream, write_stream = await self._async_exit_stack.enter_async_context(client_context)
                
                self.session = await self._async_exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await self.session.initialize()
                self.tools = await load_mcp_tools(self.session)
                logger.info(f"MCP Session initialized. Loaded {len(self.tools)} tools.")
                return
            except BaseException as e:
                logger.warning(f"Failed to connect to MCP (attempt {attempt + 1}): {e}. Retrying in 2s...")
                await asyncio.sleep(2)
        logger.error("Failed to connect to MCP after 5 attempts.")

    async def disconnect(self):
        try:
            await self._async_exit_stack.aclose()
        except Exception as e:
            logger.debug(f"MCP disconnect: {e}")
        self.session = None

from app.core.config import settings

mcp_service = MCPService(
    sse_url=settings.mcp_server_url,
    api_token=getattr(settings, "mcp_api_token", None)
)
