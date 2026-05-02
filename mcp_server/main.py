import os
from loguru import logger
import langchain_google_genai.chat_models

# Monkey patch for NeMo Guardrails + LangChain Google GenAI >= 2.0 compatibility
original_generate = langchain_google_genai.chat_models.ChatGoogleGenerativeAI._generate
def patched_generate(self, messages, stop=None, run_manager=None, **kwargs):
    if "max_tokens" in kwargs:
        kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
    return original_generate(self, messages, stop, run_manager, **kwargs)
langchain_google_genai.chat_models.ChatGoogleGenerativeAI._generate = patched_generate

original_agenerate = langchain_google_genai.chat_models.ChatGoogleGenerativeAI._agenerate
async def patched_agenerate(self, messages, stop=None, run_manager=None, **kwargs):
    if "max_tokens" in kwargs:
        kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
    return await original_agenerate(self, messages, stop, run_manager, **kwargs)
langchain_google_genai.chat_models.ChatGoogleGenerativeAI._agenerate = patched_agenerate


from fastmcp import FastMCP
from nemoguardrails import RailsConfig, LLMRails

from app.core.config import settings
from app.tools.search import search_portfolio_images
from app.tools.prompt import get_portfolio_context

mcp = FastMCP("PortfolioMCP")

# Map Gemini API key for NeMo Guardrails
os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key or ""

# Initialize NeMo Guardrails Configuration
try:
    # Adjust path if running from root directory
    config_path = os.path.join(os.path.dirname(__file__), "app", "core", "guardrails")
    config = RailsConfig.from_path(config_path)
    guardrails = LLMRails(config)
    logger.info("NeMo Guardrails successfully initialized.")
except Exception as e:
    logger.error(f"Failed to load NeMo Guardrails config: {e}")
    guardrails = None

async def safe_search_async(query: str) -> str:
    # 1. NeMo Guardrails Evaluation Middleware
    if guardrails:
        try:
            # We use LLMRails.check_async() to quickly validate input safety
            res = await guardrails.check_async(messages=[{"role": "user", "content": query}])
            if res and res.is_safe is False:
                return "Blocked by NeMo Guardrails: Query violates safety guidelines."
        except Exception as e:
            logger.error(f"Guardrail check failed: {e}")
    
    # 2. Proceed to actual LangChain Milvus Search
    return search_portfolio_images(query)


@mcp.tool()
async def search_portfolio(query: str) -> str:
    """
    Search for images in the photography portfolio using semantic understanding.
    Returns a list of matching images and their URLs.
    """
    return await safe_search_async(query)


@mcp.prompt
def fetch_base_prompt() -> str:
    """
    Retrieves the base persona prompt and Saif's parsed PDF CV context from R2.
    Call this at the beginning of interactions to understand the agent's identity.
    """
    return get_portfolio_context()


# Create ASGI app for production Streamable HTTP transport (replaces deprecated SSE)
app = mcp.http_app()

if __name__ == "__main__":
    import uvicorn
    # For local development testing
    logger.info("Starting FastMCP via uvicorn (HTTP Transport)")
    uvicorn.run("main:app", host="0.0.0.0", port=settings.mcp_port, reload=True)
