import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from loguru import logger


class MCPService:
    def __init__(self, sse_url: str):
        self.sse_url = sse_url
        self._async_exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self.tools = []

    async def connect(self):
        logger.info(f"Connecting to MCP SSE endpoint: {self.sse_url}")
        for attempt in range(5):
            try:
                read_stream, write_stream = await self._async_exit_stack.enter_async_context(
                    sse_client(self.sse_url)
                )
                self.session = await self._async_exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await self.session.initialize()
                self.tools = await load_mcp_tools(self.session)
                logger.info(f"MCP Session initialized. Loaded {len(self.tools)} tools.")
                return
            except Exception as e:
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

mcp_service = MCPService(sse_url=settings.mcp_server_url)
