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
        self.base_prompt: str = ""

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

                # Cache the base prompt at startup so we don't fetch it per-request
                try:
                    res = await self.session.get_prompt("fetch_base_prompt")
                    if res.messages and len(res.messages) > 0:
                        self.base_prompt = res.messages[0].content.text
                        logger.info("Base prompt cached successfully.")
                except Exception as e:
                    logger.warning(f"Could not cache base prompt: {e}")

                return
            except Exception as e:
                logger.warning(f"Failed to connect to MCP (attempt {attempt + 1}): {e}. Retrying in 2s...")
                await asyncio.sleep(2)
        logger.error("Failed to connect to MCP after 5 attempts.")

    async def disconnect(self):
        await self._async_exit_stack.aclose()
        self.session = None


# Use config for the URL instead of hardcoding
from app.core.config import settings

mcp_service = MCPService(sse_url=settings.mcp_server_url)
