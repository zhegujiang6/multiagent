"""Ticket Service — ticket lifecycle management and state machine."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.ticket import Ticket, TicketEvent
from app.agents.ticket_agent import TicketAgent

logger = logging.getLogger("customer_service.services.ticket")

# ── State Machine ──

VALID_TRANSITIONS: dict[str, list[str]] = {
    "new": ["assigned"],
    "assigned": ["in_progress"],
    "in_progress": ["pending", "waiting", "resolved"],
    "pending": ["in_progress", "resolved"],
    "waiting": ["in_progress", "resolved"],
    "resolved": ["closed", "reopened"],
    "closed": ["reopened"],
    "reopened": ["in_progress"],
}

DISPLAY_ID_PREFIX = "TK"


def _validate_transition(from_status: str, to_status: str):
    """Raise ValueError if transition is invalid."""
    valid = VALID_TRANSITIONS.get(from_status, [])
    if to_status not in valid:
        raise ValueError(
            f"Invalid ticket transition: {from_status} → {to_status}. "
            f"Valid transitions: {valid}"
        )


async def _generate_display_id(session: AsyncSession) -> str:
    """Generate a unique display ID like TK-20240701-0001."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"{DISPLAY_ID_PREFIX}-{today}-"
    stmt = select(func.count(Ticket.id)).where(Ticket.display_id.like(f"{prefix}%"))
    result = await session.execute(stmt)
    count = result.scalar() or 0
    return f"{prefix}{count + 1:04d}"


async def create_ticket(
    title: str,
    conversation_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    description: str | None = None,
    category: str | None = None,
    priority: str = "P3",
    assigned_to: str | None = None,
    assigned_dept: str | None = None,
) -> Ticket:
    """Create a new ticket."""
    async with async_session_factory() as session:
        display_id = await _generate_display_id(session)

        # Calculate SLA deadlines
        response_deadline, resolve_deadline = TicketAgent.calc_sla_deadlines(priority)

        ticket = Ticket(
            display_id=display_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status="new",
            assigned_to=assigned_to,
            assigned_dept=assigned_dept,
            sla_deadline=resolve_deadline,
            sla_response_deadline=response_deadline,
        )
        session.add(ticket)

        # Log creation event
        event = TicketEvent(
            ticket_id=ticket.id,
            from_status=None,
            to_status="new",
            triggered_by="system",
            comment="工单自动创建",
        )
        session.add(event)

        await session.flush()
        await session.refresh(ticket)
        await session.commit()
        return ticket


async def _auto_extract_knowledge(ticket_id: uuid.UUID | None, conversation_id: uuid.UUID):
    """Background task: extract knowledge from resolved ticket conversations.

    Self-evolution closed loop:
      - confidence >= 0.8 → auto-approved + published to Qdrant (no human needed)
      - confidence >= 0.6 → saved as draft for human review
      - confidence < 0.6  → discarded (not valuable enough)
    """
    try:
        from app.services.knowledge_extraction_service import extract_knowledge_from_conversation
        from app.services.knowledge_service import (
            create_knowledge_article,
            auto_approve_article,
            AUTO_APPROVE_CONFIDENCE,
            DRAFT_CONFIDENCE,
        )

        pairs = await extract_knowledge_from_conversation(str(conversation_id))
        auto_approved = 0
        drafted = 0
        discarded = 0

        for pair in pairs:
            confidence = pair.get("confidence", 0.5)
            content = f"问题：{pair['question']}\n\n答案：{pair['answer']}"

            article = await create_knowledge_article(
                title=pair["title"],
                content=content,
                category=pair.get("category", "other"),
                tags=pair.get("tags", []),
                source_ticket_id=ticket_id,
                source_conversation_id=conversation_id,
                status="draft",  # Start as draft, auto-approve below if eligible
                meta_info={
                    "question": pair["question"],
                    "confidence": confidence,
                },
            )

            if confidence >= AUTO_APPROVE_CONFIDENCE:
                await auto_approve_article(article.id)
                auto_approved += 1
            elif confidence >= DRAFT_CONFIDENCE:
                drafted += 1
            else:
                # Low confidence — delete the draft, not worth human review
                from app.services.knowledge_service import delete_article
                await delete_article(article.id)
                discarded += 1

        if auto_approved or drafted:
            logger.info(
                f"[Self-Evolution] Ticket {ticket_id}: "
                f"auto-approved={auto_approved}, drafted={drafted}, discarded={discarded}"
            )
    except Exception as e:
        logger.warning(
            f"Auto-extraction failed for ticket {ticket_id}: {e} (non-fatal)"
        )


async def update_ticket_status(
    ticket_id: uuid.UUID,
    to_status: str,
    triggered_by: str = "system",
    comment: str | None = None,
    resolution: str | None = None,
    assigned_to: str | None = None,
    assigned_dept: str | None = None,
) -> Ticket:
    """Update ticket status with state machine validation."""
    async with async_session_factory() as session:
        ticket = await session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate transition
        _validate_transition(ticket.status, to_status)

        from_status = ticket.status
        ticket.status = to_status
        ticket.updated_at = datetime.now(timezone.utc)

        if to_status == "resolved":
            ticket.resolved_at = datetime.now(timezone.utc)
            if resolution:
                ticket.resolution = resolution
        elif to_status == "closed":
            ticket.closed_at = datetime.now(timezone.utc)
        elif to_status == "reopened":
            ticket.resolved_at = None
            ticket.closed_at = None

        if assigned_to is not None:
            ticket.assigned_to = assigned_to
        if assigned_dept is not None:
            ticket.assigned_dept = assigned_dept

        # Log event
        event = TicketEvent(
            ticket_id=ticket.id,
            from_status=from_status,
            to_status=to_status,
            triggered_by=triggered_by,
            comment=comment,
        )
        session.add(event)

        await session.flush()
        await session.refresh(ticket)
        await session.commit()

        # ── Auto-extract knowledge when ticket is resolved ──
        if to_status == "resolved" and ticket.conversation_id:
            asyncio.create_task(_auto_extract_knowledge(ticket.id, ticket.conversation_id))

        return ticket


async def get_ticket(ticket_id: uuid.UUID) -> Ticket | None:
    """Get a ticket by ID, with events loaded."""
    async with async_session_factory() as session:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.events))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    """List tickets with filters and pagination."""
    async with async_session_factory() as session:
        stmt = select(Ticket)

        if status:
            stmt = stmt.where(Ticket.status == status)
        if priority:
            stmt = stmt.where(Ticket.priority == priority)
        if assigned_to:
            stmt = stmt.where(Ticket.assigned_to == assigned_to)
        if customer_id:
            stmt = stmt.where(Ticket.customer_id == customer_id)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar() or 0

        # Paginated query
        stmt = stmt.order_by(Ticket.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        tickets = list(result.scalars().all())

        return tickets, total


async def add_ticket_comment(
    ticket_id: uuid.UUID,
    comment: str,
    triggered_by: str = "agent",
):
    """Add a comment to a ticket without changing status."""
    async with async_session_factory() as session:
        event = TicketEvent(
            ticket_id=ticket_id,
            from_status=None,
            to_status="comment",
            triggered_by=triggered_by,
            comment=comment,
        )
        session.add(event)
