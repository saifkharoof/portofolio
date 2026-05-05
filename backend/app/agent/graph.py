"""LangGraph agent — orchestrates the conversation with tool calling."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from app.core.config import settings
from app.services.mcp_client import mcp_service


# ---------------------------------------------------------------------------
# Singleton LLM — instantiated once, reused across all requests
# ---------------------------------------------------------------------------
_llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model_name,
    google_api_key=settings.gemini_api_key,
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Agent node
# ---------------------------------------------------------------------------

async def agent_node(state: AgentState):
    """
    The main LLM node. Uses the cached base prompt from MCP,
    binds tools, and generates a response.
    """
    llm = _llm

    # Bind tools dynamically (tool list is stable after startup)
    tools = mcp_service.tools
    if tools:
        llm = llm.bind_tools(tools)

    messages = list(state["messages"])

    # Prepend the system message if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        system_content = mcp_service.base_prompt or "You are a helpful photography portfolio assistant."
        messages = [SystemMessage(content=system_content)] + messages

    # Strip heavy base64 images from history before sending to the LLM.
    # We keep only the most recent HumanMessage's image (if any) and replace
    # older ones with a lightweight placeholder to save tokens.
    cleaned = []
    for i, msg in enumerate(messages):
        is_last_message = (i == len(messages) - 1)
        if getattr(msg, "type", "") == "human" and isinstance(msg.content, list):
            new_parts = []
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    # Strictly keep the image payload ONLY if it's attached to the CURRENT active turn.
                    # This prevents old images from bleeding into future context.
                    if is_last_message:
                        new_parts.append(part)
                    else:
                        new_parts.append({"type": "text", "text": "[User uploaded an image]"})
                else:
                    new_parts.append(part)
            cleaned.append(HumanMessage(content=new_parts))
        else:
            cleaned.append(msg)
    messages = cleaned

    # --- History Pruning ---
    # Keep only the system message + the last 6 messages (3 turns)
    # This prevents the LLM from hallucinating old tool calls or hitting token limits
    MAX_HISTORY = 6
    if len(messages) > MAX_HISTORY + 1:
        sys_msg = messages[0]
        recent = messages[-MAX_HISTORY:]
        # Gemini strictly requires the conversation history (after system prompt)
        # to start with a HumanMessage. If our slice starts with AI or Tool,
        # we must prepend older messages until we hit a HumanMessage.
        while recent and getattr(recent[0], "type", "") != "human":
            idx = len(messages) - len(recent) - 1
            if idx > 0:
                recent.insert(0, messages[idx])
            else:
                break
        messages = [sys_msg] + recent

    # --- Gemini Strict Alternation Sanitization ---
    # Gemini strictly requires: Human -> AI -> Human -> AI, and AI(tool_calls) -> Tool.
    # If a mid-conversation failure occurs (e.g. timeout), history gets sequential HumanMessages.
    sanitized = []
    for m in messages:
        if not sanitized:
            sanitized.append(m)
            continue
            
        prev = sanitized[-1]
        
        # Merge consecutive HumanMessages
        if getattr(m, "type", "") == "human" and getattr(prev, "type", "") == "human":
            merged_content = []
            for msg_obj in [prev, m]:
                if isinstance(msg_obj.content, str):
                    merged_content.append({"type": "text", "text": msg_obj.content})
                elif isinstance(msg_obj.content, list):
                    merged_content.extend(msg_obj.content)
            sanitized[-1] = HumanMessage(content=merged_content)
        # Merge consecutive AIMessages without tool calls
        elif getattr(m, "type", "") == "ai" and getattr(prev, "type", "") == "ai":
            if not getattr(m, "tool_calls", []) and not getattr(prev, "tool_calls", []):
                sanitized[-1] = AIMessage(content=f"{prev.content}\n\n{m.content}")
            else:
                sanitized.append(m)
        else:
            sanitized.append(m)
            
    # Drop orphaned tool calls or tool responses
    final_messages = []
    from loguru import logger
    for i, m in enumerate(sanitized):
        if getattr(m, "type", "") == "ai" and getattr(m, "tool_calls", []):
            if i + 1 < len(sanitized) and getattr(sanitized[i+1], "type", "") == "tool":
                final_messages.append(m)
            else:
                logger.warning("Dropping orphaned AI tool call to satisfy Gemini strict alternation.")
        elif getattr(m, "type", "") == "tool":
            if not final_messages or getattr(final_messages[-1], "type", "") != "ai" or not getattr(final_messages[-1], "tool_calls", []):
                logger.warning("Dropping orphaned Tool response to satisfy Gemini strict alternation.")
            else:
                final_messages.append(m)
        else:
            final_messages.append(m)

    response = await llm.ainvoke(final_messages)
    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Tool node — injects image_base64 for MCP search, then cleans up
# ---------------------------------------------------------------------------

async def tool_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    injected = False
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        latest_base64 = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) and isinstance(msg.content, list):
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:image/"):
                            latest_base64 = url.split("base64,")[1]
                            break
                if latest_base64:
                    break

        if latest_base64:
            for tc in last_message.tool_calls:
                if tc["name"] == "search_portfolio":
                    tc["args"]["image_base64"] = latest_base64
                    injected = True

    node = ToolNode(mcp_service.tools)
    result = await node.ainvoke(state)

    # Clean up the massive base64 string so it doesn't exceed
    # the LLM token limit on the next turn.
    if injected:
        for tc in last_message.tool_calls:
            if tc["name"] == "search_portfolio" and "image_base64" in tc["args"]:
                tc["args"]["image_base64"] = None

    return result


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Build & compile the graph
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)
