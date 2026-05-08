"""LangGraph agent — orchestrates the conversation with tool calling."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from app.core.config import settings
from app.services.mcp_client import mcp_service


_llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model_name,
    google_api_key=settings.gemini_api_key,
)

_cached_bound_llm = None


def _get_bound_llm():
    global _cached_bound_llm
    if _cached_bound_llm is not None:
        return _cached_bound_llm
    if mcp_service.tools:
        _cached_bound_llm = _llm.bind_tools(mcp_service.tools)
    return _cached_bound_llm


IMAGE_DESCRIPTION_PROMPT = (
    "You are a semantic image retrieval expert. Given an image, produce a concise "
    "search-friendly description (2-4 sentences, max 200 characters) that captures "
    "only the visual elements most useful for finding similar photographs in a portfolio. "
    "Focus on: subject type, lighting mood (e.g. golden hour, moody, dramatic), "
    "color palette, composition style, and any distinctive visual traits. "
    "Do NOT write a narrative story. Do NOT describe technical camera settings. "
    "Output ONLY the description text, no preamble, no bullet points."
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    image_description: str | None
    image_described: bool
    search_context: str
    last_search_query: str
    previous_results: str
    system_prompt: str


def _has_image_in_message(msg: HumanMessage) -> str | None:
    if not isinstance(msg, HumanMessage):
        return None
    if not isinstance(msg.content, list):
        return None
    for part in msg.content:
        if isinstance(part, dict) and part.get("type") == "image_url":
            url = part.get("image_url", {}).get("url", "")
            if url.startswith("data:image/"):
                return url.split("base64,")[1]
    return None


async def describe_image_node(state: AgentState) -> AgentState:
    logger.debug(f"describe_image_node entry, image_described={state.get('image_described')}")
    messages = state["messages"]
    last_message = messages[-1]

    image_base64 = _has_image_in_message(last_message)

    user_text = ""
    if isinstance(last_message.content, list):
        for part in last_message.content:
            if isinstance(part, dict) and part.get("type") == "text":
                user_text = part.get("text", "")
                break
    elif isinstance(last_message.content, str):
        user_text = last_message.content

    if not image_base64:
        logger.debug(f"describe_image_node: no image, using text query: {user_text[:50]!r}")
        return {"image_description": user_text.strip() or None, "image_described": True}

    try:
        response = await _llm.ainvoke([
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT}
            ])
        ])

        description = response.content.strip() if response.content else ""
        logger.debug(f"Image description generated ({len(description)} chars)")

        combined = description
        if user_text.strip() and user_text.strip().lower() not in ("image matching", ""):
            combined = f"{description}\n\nAdditionally, the user requested: {user_text.strip()}"

        return {"image_description": combined, "image_described": True}

    except Exception as e:
        logger.error(f"Image description generation failed: {e}")
        return {"image_description": "", "image_described": True}


def _route_after_describe(state: AgentState) -> str:
    return "agent"


async def agent_node(state: AgentState) -> AgentState:
    llm = _get_bound_llm() or _llm.bind_tools(mcp_service.tools)

    messages = list(state["messages"])

    if not messages or not isinstance(messages[0], SystemMessage):
        system_content = state.get("system_prompt") or "You are a helpful photography portfolio assistant."
        messages = [SystemMessage(content=system_content)] + messages

    cleaned = []
    for i, msg in enumerate(messages):
        is_last_message = (i == len(messages) - 1)
        if getattr(msg, "type", "") == "human" and isinstance(msg.content, list):
            new_parts = []
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
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

    MAX_HISTORY = 24
    if len(messages) > MAX_HISTORY + 1:
        sys_msg = messages[0]
        recent = messages[-MAX_HISTORY:]
        while recent and getattr(recent[0], "type", "") != "human":
            idx = len(messages) - len(recent) - 1
            if idx > 0:
                recent.insert(0, messages[idx])
            else:
                break
        messages = [sys_msg] + recent

    sanitized = []
    for m in messages:
        if not sanitized:
            sanitized.append(m)
            continue

        prev = sanitized[-1]

        if getattr(m, "type", "") == "human" and getattr(prev, "type", "") == "human":
            merged_content = []
            for msg_obj in [prev, m]:
                if isinstance(msg_obj.content, str):
                    merged_content.append({"type": "text", "text": msg_obj.content})
                elif isinstance(msg_obj.content, list):
                    merged_content.extend(msg_obj.content)
            sanitized[-1] = HumanMessage(content=merged_content)
        elif getattr(m, "type", "") == "ai" and getattr(prev, "type", "") == "ai":
            if not getattr(m, "tool_calls", []) and not getattr(prev, "tool_calls", []):
                sanitized[-1] = AIMessage(content=f"{prev.content}\n\n{m.content}")
            else:
                sanitized.append(m)
        else:
            sanitized.append(m)

    final_messages = []
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


async def tool_node(state: AgentState) -> AgentState:
    logger.debug(f"tool_node entry, image_description={'<set>' if state.get('image_description') else '<none>'}")
    if not state.get("image_description") or not state["image_description"].strip():
        logger.debug("tool_node: no image_description, returning END")
        return END
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tc in last_message.tool_calls:
            if tc["name"] == "search_portfolio":
                query = state.get("image_description") or ""
                tc["args"]["query"] = query

    node = ToolNode(mcp_service.tools)
    result = await node.ainvoke(state)
    if state.get("image_description"):
        state["image_description"] = None

    new_results = ""
    tool_msgs = [m for m in result.get("messages", []) if getattr(m, "type", "") == "tool"]
    for tm in tool_msgs:
        if hasattr(tm, "content") and isinstance(tm.content, str):
            new_results = tm.content.strip()
            break

    if new_results:
        result["previous_results"] = new_results
        result["last_search_query"] = state.get("last_search_query", "") or state.get("image_description", "")
        if state.get("search_context"):
            result["search_context"] = state.get("search_context", "") + "\n\n" + new_results
        else:
            result["search_context"] = new_results

    return result


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        if not state.get("image_description") or not state["image_description"].strip():
            logger.debug("should_continue: tool_calls present but no image_description, returning END")
            return END
        return "tools"
    return END


workflow = StateGraph(AgentState)
workflow.add_node("describe_image", describe_image_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "describe_image")
workflow.add_conditional_edges("describe_image", _route_after_describe, {"agent": "agent"})
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

app_graph = workflow.compile(checkpointer=MemorySaver())