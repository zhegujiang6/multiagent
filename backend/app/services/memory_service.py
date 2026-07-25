"""Task-oriented conversation memory and safe cross-conversation user memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.core.security import mask_pii
from app.models.memory import ConversationMemory, UserMemory
from app.models.conversation import Conversation
from app.models.message import Message

RECENT_MESSAGE_LIMIT = 8
MAX_ACTIONS = 4
MAX_PENDING_ITEMS = 3
MAX_TAGS = 4
MAX_SUMMARY_LENGTH = 800

SATISFACTION_SCORES = {
    "satisfied": 1.0,
    "unknown": 0.0,
    "dissatisfied": -1.0,
}


def _short_text(value: str | None, limit: int = 240) -> str:
    return mask_pii((value or "").strip())[:limit]


def _append_unique(items: list[str], value: str | None, limit: int) -> list[str]:
    clean = _short_text(value)
    if not clean:
        return items[-limit:]
    return [*([item for item in items if item != clean]), clean][-limit:]


def _sentiment_label(sentiment: dict[str, Any] | None) -> str | None:
    if not sentiment:
        return None
    label = sentiment.get("label")
    return str(label) if label else None


def derive_satisfaction(
    sentiment: dict[str, Any] | None,
    existing: str = "unknown",
    explicit_feedback: str | None = None,
) -> str:
    """Prefer explicit feedback, otherwise use a conservative sentiment signal."""
    if explicit_feedback in {"helpful", "resolved"}:
        return "satisfied"
    if explicit_feedback in {"unhelpful", "followup", "escalated"}:
        return "dissatisfied"

    label = _sentiment_label(sentiment)
    if label == "satisfied":
        return "satisfied"
    if label in {"dissatisfied", "angry", "desperate"}:
        return "dissatisfied"
    return existing if existing in SATISFACTION_SCORES else "unknown"


def _route_from_state(state: dict[str, Any]) -> str | None:
    for decision in reversed(state.get("agent_decisions") or []):
        if decision.get("agent") == "orchestrator":
            route = decision.get("decision")
            if route:
                return str(route)
    return None


def _build_tags(intent: str | None, sentiment: str | None, satisfaction: str, status: str) -> list[str]:
    values = [
        f"intent:{intent}" if intent else "",
        f"sentiment:{sentiment}" if sentiment else "",
        f"satisfaction:{satisfaction}",
        f"status:{status}",
    ]
    return [value for value in values if value][:MAX_TAGS]


def _render_summary(
    *,
    goal: str | None,
    completed_actions: list[str],
    pending_items: list[str],
    next_action: str | None,
    status: str,
) -> str:
    sections = []
    if goal:
        sections.append(f"用户目标：{goal}")
    if completed_actions:
        sections.append(f"已完成：{'；'.join(completed_actions)}")
    if pending_items:
        sections.append(f"待处理：{'；'.join(pending_items)}")
    if next_action:
        sections.append(f"下一步：{next_action}")
    sections.append(f"会话状态：{status}")
    return "\n".join(sections)[:MAX_SUMMARY_LENGTH]


def _memory_dict(memory: ConversationMemory | None) -> dict[str, Any]:
    if memory is None:
        return {
            "goal": "",
            "completed_actions": [],
            "pending_items": [],
            "next_action": "",
            "summary": "",
            "status": "active",
            "intent": None,
            "sentiment": None,
            "satisfaction": "unknown",
            "tags": [],
            "message_count": 0,
            "turn_count": 0,
        }
    return {
        "goal": memory.goal or "",
        "completed_actions": list(memory.completed_actions or []),
        "pending_items": list(memory.pending_items or []),
        "next_action": memory.next_action or "",
        "summary": memory.summary or "",
        "status": memory.status,
        "intent": memory.intent,
        "sentiment": memory.sentiment,
        "satisfaction": memory.satisfaction,
        "tags": list(memory.tags or []),
        "message_count": memory.message_count,
        "turn_count": memory.turn_count,
    }


def _user_memory_dict(memory: UserMemory | None) -> dict[str, Any]:
    if memory is None:
        return {
            "conversation_count": 0,
            "resolved_count": 0,
            "escalation_count": 0,
            "latest_sentiment": None,
            "satisfaction": "unknown",
            "preferences": [],
            "open_tasks": [],
            "tags": [],
            "last_session_summary": "",
        }
    return {
        "conversation_count": memory.conversation_count,
        "resolved_count": memory.resolved_count,
        "escalation_count": memory.escalation_count,
        "latest_sentiment": memory.latest_sentiment,
        "satisfaction": memory.satisfaction,
        "preferences": list(memory.preferences or []),
        "open_tasks": list(memory.open_tasks or []),
        "tags": list(memory.tags or []),
        "last_session_summary": memory.last_session_summary or "",
    }


def format_memory_for_prompt(session_memory: dict[str, Any], user_memory: dict[str, Any]) -> str:
    """Create a bounded prompt section that replaces distant raw messages."""
    session_summary = _short_text(str(session_memory.get("summary", "")), MAX_SUMMARY_LENGTH)
    open_tasks = [_short_text(str(item), 180) for item in user_memory.get("open_tasks", [])[:3]]
    last_session_summary = _short_text(str(user_memory.get("last_session_summary", "")), 420)
    preferences = [_short_text(str(item), 120) for item in user_memory.get("preferences", [])[:3]]
    lines = ["【持续记忆】"]
    if session_summary:
        lines.append(session_summary)
    if user_memory.get("conversation_count"):
        lines.append(f"历史会话数：{user_memory['conversation_count']}")
    if user_memory.get("satisfaction") and user_memory["satisfaction"] != "unknown":
        lines.append(f"用户满意度：{user_memory['satisfaction']}")
    if open_tasks:
        lines.append(f"跨会话待办：{'；'.join(open_tasks)}")
    elif last_session_summary and not session_summary:
        lines.append(f"最近服务记录：{last_session_summary}")
    if preferences:
        lines.append(f"服务偏好：{'；'.join(preferences)}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


async def ensure_user_memory(customer_id: str) -> None:
    """Start a user-memory record when a non-shared customer starts a conversation."""
    if not customer_id or customer_id == "anonymous":
        return
    async with async_session_factory() as session:
        memory = await session.get(UserMemory, customer_id)
        if memory is None:
            session.add(UserMemory(customer_id=customer_id, conversation_count=1))
        else:
            memory.conversation_count += 1
            memory.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def load_memory_context(conversation_id: str, customer_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load compact session and user memory before constructing agent context."""
    async with async_session_factory() as session:
        conversation_memory = await session.scalar(
            select(ConversationMemory).where(ConversationMemory.conversation_id == uuid.UUID(conversation_id))
        )
        user_memory = None
        if customer_id and customer_id != "anonymous":
            user_memory = await session.get(UserMemory, customer_id)
        return _memory_dict(conversation_memory), _user_memory_dict(user_memory)


async def get_conversation_memory(conversation_id: str) -> dict[str, Any] | None:
    async with async_session_factory() as session:
        memory = await session.scalar(
            select(ConversationMemory).where(ConversationMemory.conversation_id == uuid.UUID(conversation_id))
        )
        return _memory_dict(memory) if memory else None


async def update_memories(
    *,
    conversation_id: str,
    customer_id: str,
    user_message: str,
    final_state: dict[str, Any],
) -> dict[str, Any]:
    """Update structured session state after each completed assistant turn."""
    conversation_uuid = uuid.UUID(conversation_id)
    intent = (final_state.get("intent") or {}).get("label")
    sentiment = final_state.get("sentiment") or {}
    sentiment_label = _sentiment_label(sentiment)
    route = _route_from_state(final_state)

    async with async_session_factory() as session:
        memory = await session.scalar(
            select(ConversationMemory).where(ConversationMemory.conversation_id == conversation_uuid)
        )
        if memory is None:
            memory = ConversationMemory(conversation_id=conversation_uuid)
            session.add(memory)

        previous_goal = memory.goal or ""
        previous_status = memory.status
        goal = previous_goal or _short_text(user_message, 400)
        if intent and memory.intent and intent != memory.intent and intent not in {"chitchat", "other"}:
            goal = _short_text(user_message, 400)

        completed = list(memory.completed_actions or [])
        pending = list(memory.pending_items or [])
        status = "active"
        next_action = "等待用户继续说明或确认处理结果"

        if final_state.get("should_escalate"):
            status = "escalated"
            completed = _append_unique(completed, "已升级至人工客服", MAX_ACTIONS)
            pending = _append_unique(pending, "等待人工客服接入", MAX_PENDING_ITEMS)
            next_action = "人工客服接入后继续处理"
        elif final_state.get("ticket_draft"):
            status = "waiting_follow_up"
            draft = final_state["ticket_draft"]
            category = _short_text(str(draft.get("category", "问题")), 80)
            completed = _append_unique(completed, f"已整理{category}工单信息", MAX_ACTIONS)
            pending = _append_unique(pending, "等待坐席确认并跟进工单", MAX_PENDING_ITEMS)
            next_action = "坐席确认工单后向用户同步进度"
        elif route == "faq_answer":
            completed = _append_unique(completed, "已提供知识库答复", MAX_ACTIONS)
            pending = []
            next_action = "等待用户确认答复是否解决问题"
        elif route == "direct_response":
            next_action = "等待用户提出具体问题"

        if final_state.get("knowledge_gap_detected"):
            pending = _append_unique(pending, "知识库待补充相关答案", MAX_PENDING_ITEMS)

        satisfaction = derive_satisfaction(sentiment, memory.satisfaction)
        message_count = await session.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_uuid)
        ) or 0
        turn_count = await session.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_uuid,
                Message.role == "customer",
            )
        ) or 0

        memory.goal = goal
        memory.completed_actions = completed[-MAX_ACTIONS:]
        memory.pending_items = pending[-MAX_PENDING_ITEMS:]
        memory.next_action = _short_text(next_action, 240)
        memory.status = status
        memory.intent = str(intent) if intent else memory.intent
        memory.sentiment = sentiment_label
        memory.satisfaction = satisfaction
        memory.tags = _build_tags(memory.intent, sentiment_label, satisfaction, status)
        memory.message_count = int(message_count)
        memory.turn_count = int(turn_count)
        memory.summary = _render_summary(
            goal=memory.goal,
            completed_actions=list(memory.completed_actions),
            pending_items=list(memory.pending_items),
            next_action=memory.next_action,
            status=status,
        )
        memory.last_compressed_at = datetime.now(timezone.utc)
        memory.updated_at = datetime.now(timezone.utc)

        user_memory = None
        if customer_id and customer_id != "anonymous":
            user_memory = await session.get(UserMemory, customer_id)
            if user_memory is None:
                user_memory = UserMemory(customer_id=customer_id, conversation_count=1)
                session.add(user_memory)
            user_memory.latest_sentiment = sentiment_label or user_memory.latest_sentiment
            user_memory.satisfaction = satisfaction
            score = SATISFACTION_SCORES[satisfaction]
            user_memory.satisfaction_score = round((user_memory.satisfaction_score * 0.7) + (score * 0.3), 4)
            if status == "escalated" and previous_status != "escalated":
                user_memory.escalation_count += 1
            if status == "resolved" and previous_status != "resolved":
                user_memory.resolved_count += 1
            task = _short_text(memory.next_action, 180)
            if status in {"escalated", "waiting_follow_up"}:
                user_memory.open_tasks = _append_unique(list(user_memory.open_tasks or []), task, 3)
            user_memory.tags = [tag for tag in memory.tags if not tag.startswith("status:")][:MAX_TAGS]
            user_memory.last_session_summary = memory.summary
            user_memory.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(memory)
        return _memory_dict(memory)


async def record_satisfaction_feedback(conversation_id: str, feedback_type: str) -> None:
    """Let explicit thumbs-up/down feedback override the inferred satisfaction label."""
    async with async_session_factory() as session:
        memory = await session.scalar(
            select(ConversationMemory).where(ConversationMemory.conversation_id == uuid.UUID(conversation_id))
        )
        if memory is None:
            return
        satisfaction = derive_satisfaction(None, memory.satisfaction, feedback_type)
        memory.satisfaction = satisfaction
        memory.tags = _build_tags(memory.intent, memory.sentiment, satisfaction, memory.status)
        memory.summary = _render_summary(
            goal=memory.goal,
            completed_actions=list(memory.completed_actions or []),
            pending_items=list(memory.pending_items or []),
            next_action=memory.next_action,
            status=memory.status,
        )
        conversation = await session.get(Conversation, uuid.UUID(conversation_id))
        if conversation and conversation.customer_id != "anonymous":
            user_memory = await session.get(UserMemory, conversation.customer_id)
            if user_memory:
                user_memory.satisfaction = satisfaction
                score = SATISFACTION_SCORES[satisfaction]
                user_memory.satisfaction_score = round(
                    (user_memory.satisfaction_score * 0.7) + (score * 0.3), 4
                )
                user_memory.updated_at = datetime.now(timezone.utc)
        await session.commit()
