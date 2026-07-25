"""Chat API — REST and WebSocket endpoints for conversation messaging."""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.chat import (
    CreateConversationRequest,
    ConversationResponse,
    SendMessageRequest,
    ChatResponse,
    MessageResponse,
)
from app.services.conversation_service import (
    create_conversation,
    get_conversation,
    get_messages,
    process_message,
    process_message_streaming,
)
from app.services.memory_service import get_conversation_memory
from app.models.conversation import Conversation
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger("customer_service.api.chat")
router = APIRouter(prefix="/api/v1", tags=["chat"])


# ── REST Endpoints ──

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_new_conversation(req: CreateConversationRequest):
    """Create a new conversation."""
    conv = await create_conversation(
        customer_id=req.customer_id,
        channel=req.channel,
    )
    return ConversationResponse.model_validate(conv)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_detail(conversation_id: uuid.UUID):
    """Get conversation details."""
    conv = await get_conversation(str(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: uuid.UUID, limit: int = 50):
    """Get paginated message history."""
    messages = await get_messages(str(conversation_id), limit=limit)
    return {
        "conversation_id": str(conversation_id),
        "messages": [MessageResponse.model_validate(m) for m in messages],
        "total": len(messages),
    }


@router.get("/conversations/{conversation_id}/memory")
async def get_conversation_memory_endpoint(conversation_id: uuid.UUID):
    """Return the compact task state used to continue this conversation."""
    conv = await get_conversation(str(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    memory = await get_conversation_memory(str(conversation_id))
    return {
        "conversation_id": str(conversation_id),
        "memory": memory,
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: uuid.UUID, req: SendMessageRequest):
    """Send a message and get the full agent response (REST)."""
    conv = await get_conversation(str(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await process_message(
        conversation_id=str(conversation_id),
        user_message=req.content,
        customer_id=conv.customer_id,
    )

    return result


@router.post("/conversations/{conversation_id}/escalate")
async def escalate_conversation(conversation_id: uuid.UUID):
    """Request human takeover."""
    conv = await get_conversation(str(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "conversation_id": str(conversation_id),
        "status": "escalating",
        "message": "正在为您转接人工客服，请稍候...",
    }


@router.post("/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: uuid.UUID):
    """Close a conversation and trigger knowledge extraction.

    When a conversation is resolved by a human agent (no ticket created),
    this endpoint closes the conversation and runs the self-evolution
    extraction pipeline in the background.
    """
    import asyncio
    from datetime import datetime, timezone
    from app.core.database import async_session_factory

    conv = await get_conversation(str(conversation_id))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Update status
    async with async_session_factory() as session:
        from sqlalchemy import update
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status="closed", closed_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        )
        await session.commit()

    # Trigger background knowledge extraction
    from app.services.knowledge_lifecycle_service import auto_extract_knowledge
    asyncio.create_task(auto_extract_knowledge(
        ticket_id=None,  # No ticket — conversation-only close
        conversation_id=conversation_id,
    ))

    return {
        "conversation_id": str(conversation_id),
        "status": "closed",
        "message": "会话已关闭，系统将在后台自动提取知识。",
    }


# ── WebSocket Endpoint ──

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, conversation_id: str = ""):
    """WebSocket endpoint for real-time chat with streaming agent updates.

    Client connects with: ws://host/api/v1/ws/chat?conversation_id={id}
    """
    await websocket_manager.connect(conversation_id, websocket)
    logger.info(f"WebSocket connected: conversation={conversation_id}")

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket_manager.send_json(websocket, {"type": "pong"})
                continue

            if msg_type == "typing":
                # Relay typing indicator (future: to human agent)
                continue

            if msg_type == "message":
                content = data.get("payload", {}).get("content", "")
                if not content:
                    await websocket_manager.send_json(websocket, {"type": "error", "payload": {"code": "empty_message", "message": "Message content is required"}})
                    continue

                conv = await get_conversation(conversation_id)
                if not conv:
                    await websocket_manager.send_json(websocket, {"type": "error", "payload": {"code": "conversation_not_found", "message": "Conversation not found"}})
                    continue

                # Process with streaming updates. The server, not the browser,
                # owns the customer identity used for durable memory.
                async for update in process_message_streaming(
                    conversation_id=conversation_id,
                    user_message=content,
                    customer_id=conv.customer_id,
                ):
                    await websocket_manager.send_json(websocket, update)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: conversation={conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket_manager.send_json(websocket, {"type": "error", "payload": {"code": "internal_error", "message": str(e)}})
        except Exception:
            pass
    finally:
        await websocket_manager.disconnect(conversation_id, websocket)
