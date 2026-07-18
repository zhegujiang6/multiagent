"""Conversation Service — orchestrates the full message processing pipeline."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.llm import get_async_llm_client
from app.core.redis import get_redis
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentState
from app.schemas.chat import AgentStatusMessage
from app.agents.registry import AgentRegistry
from app.agents.orchestrator import OrchestratorAgent

logger = logging.getLogger("customer_service.services.conversation")

# Role mapping for LangGraph compatibility: DB roles → standard LLM roles
ROLE_MAP = {
    "customer": "user",
    "agent": "assistant",
    "system": "system",
}


async def create_conversation(
    customer_id: str,
    channel: str = "web",
    meta_info: dict | None = None,
) -> Conversation:
    """Create a new conversation."""
    async with async_session_factory() as session:
        conv = Conversation(
            customer_id=customer_id,
            channel=channel,
            status="active",
            meta_info=meta_info or {},
        )
        session.add(conv)
        await session.flush()
        await session.refresh(conv)
        await session.commit()
        return conv


async def get_conversation(conversation_id: str) -> Conversation | None:
    """Get a conversation by ID."""
    async with async_session_factory() as session:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_messages(conversation_id: str, limit: int = 50) -> list[Message]:
    """Get recent messages for a conversation."""
    async with async_session_factory() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())[::-1]  # Reverse to chronological


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    content_type: str = "text",
    meta_info: dict | None = None,
) -> Message:
    """Save a message to the database."""
    async with async_session_factory() as session:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
            meta_info=meta_info or {},
        )
        session.add(msg)
        await session.flush()
        await session.refresh(msg)
        await session.commit()
        return msg


async def log_agent_run(
    conversation_id: str,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    latency_ms: int,
    tokens_used: int | None = None,
    model_used: str | None = None,
    error: str | None = None,
):
    """Log an agent execution to the database."""
    async with async_session_factory() as session:
        run = AgentRun(
            conversation_id=conversation_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=output_summary,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            model_used=model_used,
            error=error,
        )
        session.add(run)
        await session.commit()


async def process_message(
    conversation_id: str,
    user_message: str,
    customer_id: str = "anonymous",
) -> dict:
    """Process a user message through the full agent pipeline.

    This is the main entry point for synchronous message processing.
    Returns the complete response including the agent's reply and any side effects.
    """
    import time
    start_time = time.monotonic()

    # 1. Save user message
    user_msg = await save_message(
        conversation_id=conversation_id,
        role="customer",
        content=user_message,
    )

    # 2. Get recent conversation history
    recent_messages = await get_messages(conversation_id)
    history = [
        {"role": ROLE_MAP.get(m.role, "user"), "content": m.content}
        for m in recent_messages[-10:]  # Last 10 messages for context
    ]

    # 3. Build initial agent state
    state = AgentState(
        messages=history,
        conversation_id=conversation_id,
        customer_id=customer_id,
    )

    # 4. Initialize agent system
    llm_client = get_async_llm_client()
    registry = AgentRegistry(llm_client).initialize()
    orchestrator = OrchestratorAgent(llm_client, registry)

    # 5. Run the agent pipeline
    try:
        final_state = await orchestrator.run(state)
    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}")
        final_state = {
            "response": "抱歉，系统暂时遇到了一些问题，正在为您转接人工客服...",
            "should_escalate": True,
            "error": str(e),
        }

    # 6. Save agent response
    response_text = final_state.get("response", "抱歉，我暂时无法处理您的请求。")
    agent_msg = await save_message(
        conversation_id=conversation_id,
        role="agent",
        content=response_text,
        meta_info={
            "intent": final_state.get("intent"),
            "sentiment": final_state.get("sentiment"),
            "decisions": final_state.get("agent_decisions", []),
            "knowledge_source_ids": final_state.get("knowledge_source_ids", []),
            "knowledge_gap_detected": final_state.get("knowledge_gap_detected", False),
            "retrieval_event_id": final_state.get("retrieval_event_id"),
        },
    )

    # 7. Update conversation
    async with async_session_factory() as session:
        conv = await session.get(Conversation, conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            # Append sentiment
            if final_state.get("sentiment"):
                trend = list(conv.sentiment_trend) if conv.sentiment_trend else []
                trend.append(final_state["sentiment"])
                conv.sentiment_trend = trend[-20:]  # Keep last 20

    elapsed = int((time.monotonic() - start_time) * 1000)
    await log_agent_run(
        conversation_id=conversation_id,
        agent_name="orchestrator",
        input_summary=user_message[:500],
        output_summary=response_text[:500],
        latency_ms=elapsed,
        model_used="agent_pipeline",
        error=final_state.get("error"),
    )
    logger.info(f"Message processed in {elapsed}ms")

    return {
        "conversation_id": conversation_id,
        "message": agent_msg,
        "ticket_created": {
            "ticket_id": final_state.get("ticket_id"),
            "draft": final_state.get("ticket_draft"),
        } if final_state.get("ticket_draft") else None,
        "escalated": final_state.get("should_escalate", False),
        "intent": final_state.get("intent"),
        "sentiment": final_state.get("sentiment"),
    }


async def process_message_streaming(
    conversation_id: str,
    user_message: str,
    customer_id: str = "anonymous",
) -> AsyncGenerator[dict, None]:
    """Process a user message and yield status updates via streaming.

    Used by the WebSocket endpoint to provide real-time feedback.
    """
    # Save user message
    user_msg = await save_message(
        conversation_id=conversation_id,
        role="customer",
        content=user_message,
    )

    # Yield: message saved
    yield {"type": "message_saved", "message_id": str(user_msg.id)}

    # Get history
    recent_messages = await get_messages(conversation_id)
    history = [
        {"role": ROLE_MAP.get(m.role, "user"), "content": m.content}
        for m in recent_messages[-10:]
    ]

    # Build state
    state = AgentState(
        messages=history,
        conversation_id=conversation_id,
        customer_id=customer_id,
    )

    # Initialize agents
    llm_client = get_async_llm_client()
    registry = AgentRegistry(llm_client).initialize()
    orchestrator = OrchestratorAgent(llm_client, registry)

    # Run preprocessing agents with status updates
    intent_agent = registry.get("intent_classifier")
    sentiment_agent = registry.get("sentiment_analyzer")

    yield {"type": "agent_status", "agent": "intent_classifier", "status": "started"}
    yield {"type": "agent_status", "agent": "sentiment_analyzer", "status": "started"}

    intent_result, sentiment_result = await asyncio.gather(
        intent_agent.execute(state),
        sentiment_agent.execute(state),
    )

    yield {"type": "agent_status", "agent": "intent_classifier", "status": "completed",
           "result": intent_result.get("intent", {}).get("label", "")}
    yield {"type": "agent_status", "agent": "sentiment_analyzer", "status": "completed",
           "result": sentiment_result.get("sentiment", {}).get("label", "")}

    # Update state and continue pipeline
    state_merged = dict(state)
    state_merged.update(intent_result)
    state_merged.update(sentiment_result)
    state = AgentState(**state_merged)

    # Profile enrichment
    profile_agent = registry.get("profile_enricher")
    yield {"type": "agent_status", "agent": "profile_enricher", "status": "started"}
    profile_result = await profile_agent.execute(state)
    yield {"type": "agent_status", "agent": "profile_enricher", "status": "completed"}
    state_merged.update(profile_result)
    state = AgentState(**state_merged)

    # Run orchestrator (route + leaf agent + synthesize)
    yield {"type": "agent_status", "agent": "orchestrator", "status": "started"}
    try:
        # orchestrator.run() has internal 25s timeout; outer 30s as safety net
        final_state = await asyncio.wait_for(
            orchestrator.run(state),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        logger.error("Orchestrator timed out after 30s")
        final_state = {
            "response": "抱歉，系统处理超时，正在为您转接人工客服，请稍候...",
            "should_escalate": True,
            "error": "Orchestrator timeout after 30s",
        }
    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}")
        final_state = {
            "response": "抱歉，系统暂时遇到了一些问题，正在为您转接人工客服...",
            "should_escalate": True,
            "error": str(e),
        }
    yield {"type": "agent_status", "agent": "orchestrator", "status": "completed"}

    # Save response
    response_text = final_state.get("response", "抱歉，我暂时无法处理您的请求。")
    agent_msg = await save_message(
        conversation_id=conversation_id,
        role="agent",
        content=response_text,
        meta_info={
            "intent": final_state.get("intent"),
            "sentiment": final_state.get("sentiment"),
            "decisions": final_state.get("agent_decisions", []),
            "knowledge_source_ids": final_state.get("knowledge_source_ids", []),
            "retrieval_event_id": final_state.get("retrieval_event_id"),
        },
    )

    # Yield ticket info if created
    if final_state.get("ticket_draft"):
        yield {
            "type": "ticket_created",
            "draft": final_state["ticket_draft"],
        }

    if final_state.get("should_escalate"):
        yield {"type": "escalating", "reason": "auto_escalation", "eta_seconds": 30}

    # Final response
    yield {
        "type": "chat_message",
        "message": {
            "id": str(agent_msg.id),
            "conversation_id": conversation_id,
            "role": "agent",
            "content": response_text,
            "content_type": "text",
            "metadata": agent_msg.meta_info,
            "created_at": agent_msg.created_at.isoformat() if agent_msg.created_at else None,
        },
    }


# Need asyncio for gather
import asyncio  # noqa: E402
