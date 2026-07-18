"""SLA Service — SLA deadline tracking and auto-escalation."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.ticket import Ticket
from app.services.ticket_service import update_ticket_status

logger = logging.getLogger("customer_service.services.sla")

# SLA thresholds
SLA_WARNING_RATIO = 0.5  # 50% of time elapsed → warn
SLA_ESCALATE_RATIO = 0.8  # 80% of time elapsed → escalate
SLA_CRITICAL_RATIO = 1.0  # 100% of time elapsed → critical escalation

# Check interval
SLA_POLL_INTERVAL_SECONDS = 30


async def check_sla_deadlines():
    """Check all active tickets for SLA violations.

    This should run as a background task in the FastAPI lifespan.
    """
    async with async_session_factory() as session:
        stmt = select(Ticket).where(
            Ticket.status.in_(["new", "assigned", "in_progress", "pending", "waiting"])
        )
        result = await session.execute(stmt)
        active_tickets = result.scalars().all()

    now = datetime.now(timezone.utc)

    for ticket in active_tickets:
        if not ticket.sla_deadline and not ticket.sla_response_deadline:
            continue

        # Check response SLA
        if ticket.sla_response_deadline:
            _check_sla(
                ticket, ticket.sla_response_deadline, now, "response",
                ticket.sla_warning_sent, ticket.sla_escalated,
            )

        # Check resolution SLA
        if ticket.sla_deadline:
            _check_sla(
                ticket, ticket.sla_deadline, now, "resolution",
                ticket.sla_warning_sent, ticket.sla_escalated,
            )


def _check_sla(
    ticket: Ticket,
    deadline: datetime,
    now: datetime,
    sla_type: str,
    warning_sent: bool,
    escalated: bool,
):
    """Check a single SLA deadline and trigger actions."""
    total_seconds = (deadline - ticket.created_at).total_seconds()
    if total_seconds <= 0:
        return

    elapsed_seconds = (now - ticket.created_at).total_seconds()
    ratio = elapsed_seconds / total_seconds

    if ratio >= SLA_CRITICAL_RATIO and not escalated:
        logger.warning(
            f"Ticket {ticket.display_id} SLA CRITICAL: {ratio:.0%} of {sla_type} time elapsed"
        )
        # Mark for escalation
        asyncio.create_task(_escalate_ticket(ticket, "critical"))

    elif ratio >= SLA_ESCALATE_RATIO and not escalated:
        logger.warning(
            f"Ticket {ticket.display_id} SLA ESCALATE: {ratio:.0%} of {sla_type} time elapsed"
        )
        asyncio.create_task(_escalate_ticket(ticket, "escalate"))

    elif ratio >= SLA_WARNING_RATIO and not warning_sent:
        logger.info(
            f"Ticket {ticket.display_id} SLA WARNING: {ratio:.0%} of {sla_type} time elapsed"
        )
        asyncio.create_task(_warn_ticket(ticket))


async def _warn_ticket(ticket: Ticket):
    """Send SLA warning."""
    try:
        async with async_session_factory() as session:
            t = await session.get(Ticket, ticket.id)
            if t:
                t.sla_warning_sent = True
                t.updated_at = datetime.now(timezone.utc)
    except Exception as e:
        logger.error(f"Failed to send SLA warning for {ticket.display_id}: {e}")


async def _escalate_ticket(ticket: Ticket, level: str):
    """Escalate a ticket based on SLA level."""
    try:
        new_priority = "P1" if level == "escalate" else "P0"
        async with async_session_factory() as session:
            t = await session.get(Ticket, ticket.id)
            if t:
                t.priority = new_priority
                t.sla_escalated = True
                t.updated_at = datetime.now(timezone.utc)

                # Recalculate SLA based on new priority
                from app.agents.ticket_agent import TicketAgent
                _, new_deadline = TicketAgent.calc_sla_deadlines(new_priority)
                t.sla_deadline = new_deadline

                # Notify via Redis pub/sub
                from app.core.redis import get_redis
                redis = await get_redis()
                await redis.publish(
                    "sla:escalations",
                    f"Ticket {t.display_id} escalated to {new_priority} ({level})",
                )
    except Exception as e:
        logger.error(f"Failed to escalate ticket {ticket.display_id}: {e}")


async def sla_polling_loop():
    """Background loop that polls SLA deadlines."""
    logger.info("SLA polling loop started")
    while True:
        try:
            await check_sla_deadlines()
        except Exception as e:
            logger.error(f"SLA check failed: {e}")
        await asyncio.sleep(SLA_POLL_INTERVAL_SECONDS)
