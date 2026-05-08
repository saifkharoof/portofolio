"""Chat streaming endpoint — connects the frontend to the LangGraph agent."""

import asyncio
import base64
from typing import List

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from loguru import logger

from app.agent.graph import app_graph
from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.chat import (
    PortfolioImage,
    SSEContent,
    SSEToolStart,
    SSEToolEnd,
    SSEDone,
    SSEError,
    SSEBusy,
)
from app.services.chat_helpers import (
    extract_raw_content,
    extract_text_chunk,
    parse_tool_images,
    validate_thread_id,
)
from app.services.mcp_client import mcp_service
router = APIRouter()

_chat_semaphore = asyncio.Semaphore(settings.chat_max_concurrent)


@router.post("/stream")
@limiter.limit(settings.rate_limit_public)
async def chat_stream(
    request: Request,
    message: str = Form(""),
    image: UploadFile = File(None),
    thread_id: str = Form("default-thread"),
):
    try:
        validate_thread_id(thread_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if message and len(message) > settings.chat_max_message_length:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {settings.chat_max_message_length} characters.",
        )

    content = []

    if message and message.strip():
        content.append({"type": "text", "text": message})

    if image and image.filename:
        try:
            image_bytes = await image.read()

            max_bytes = settings.chat_max_image_size_mb * 1024 * 1024
            if len(image_bytes) > max_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image too large. Maximum {settings.chat_max_image_size_mb}MB.",
                )

            if image_bytes[:3] == b"\xff\xd8\xff":
                detected_mime = "image/jpeg"
            elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                detected_mime = "image/png"
            elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
                detected_mime = "image/webp"
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported image format. Use JPEG, PNG, or WebP.",
                )

            base64_img = base64.b64encode(image_bytes).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{detected_mime};base64,{base64_img}"},
            })
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    if not content:
        raise HTTPException(status_code=400, detail="Must provide either text message or image.")

    human_msg = HumanMessage(content=content)
    config = {"configurable": {"thread_id": thread_id}}

    if _chat_semaphore._value <= 0:
        async def busy_generator():
            evt = SSEBusy(type="busy")
            yield f"data: {evt.model_dump_json()}\n\n"

        return StreamingResponse(busy_generator(), media_type="text/event-stream")

    async def event_generator():
        async with _chat_semaphore:
            try:
                # Fetch base prompt from MCP at the start of each conversation
                try:
                    res = await mcp_service.session.get_prompt("fetch_base_prompt")
                    base_prompt = res.messages[0].content.text if res.messages else "You are a helpful photography portfolio assistant."
                    logger.info("Base prompt fetched from MCP.")
                except Exception as e:
                    base_prompt = "You are a helpful photography portfolio assistant."
                    logger.warning(f"Could not fetch base prompt: {e}")

                async for event in app_graph.astream_events(
                    {"messages": [human_msg], "image_description": None, "image_described": False, "search_context": "", "last_search_query": "", "previous_results": "", "system_prompt": base_prompt},
                    config,
                    version="v2",
                ):
                    event_type = event.get("event", "")

                    if event_type == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        text = extract_text_chunk(chunk.content)
                        if text:
                            evt = SSEContent(type="content", text=text)
                            yield f"data: {evt.model_dump_json()}\n\n"

                    elif event_type == "on_tool_start":
                        name = event.get("name", "")
                        if name in ("search_portfolio", "describe_image"):
                            evt = SSEToolStart(type="tool_start", name=name)
                            yield f"data: {evt.model_dump_json()}\n\n"

                    elif event_type == "on_tool_end":
                        tool_output = event["data"].get("output")
                        images: List[PortfolioImage] = []
                        if tool_output is not None:
                            raw = extract_raw_content(tool_output)
                            images = parse_tool_images(raw)
                        evt = SSEToolEnd(type="tool_end", name=event.get("name", ""), images=images)
                        yield f"data: {evt.model_dump_json()}\n\n"

                yield f"data: {SSEDone(type='done').model_dump_json()}\n\n"

            except Exception as e:
                logger.error(f"Error during stream: {e}")
                evt = SSEError(type="error", detail=str(e))
                yield f"data: {evt.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")