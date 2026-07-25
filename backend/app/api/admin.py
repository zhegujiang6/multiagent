"""Admin API — dashboard metrics and monitoring."""

import logging

from fastapi import APIRouter
from sqlalchemy import select, func

from app.core.database import async_session_factory
from app.models.conversation import Conversation
from app.models.agent_run import AgentRun
from app.clients.java_ticket_client import TicketServiceError, get_java_ticket_client

logger = logging.getLogger("customer_service.api.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/metrics")
async def get_dashboard_metrics():
    """Get overview metrics for the admin dashboard."""
    async with async_session_factory() as session:
        # Active conversations
        active_conv_stmt = select(func.count(Conversation.id)).where(
            Conversation.status == "active"
        )
        active_conversations = (await session.execute(active_conv_stmt)).scalar() or 0

        # Agent runs today
        today_runs_stmt = select(func.count(AgentRun.id)).where(
            func.date(AgentRun.created_at) == func.current_date()
        )
        agent_runs_today = (await session.execute(today_runs_stmt)).scalar() or 0

    tickets_by_status: dict[str, int] = {}
    total_tickets = 0
    client = get_java_ticket_client()
    try:
        all_tickets = await client.list_tickets(page=1, page_size=1)
        total_tickets = int(all_tickets.get("total", 0))
        for status in (
            "NEW",
            "ASSIGNED",
            "IN_PROGRESS",
            "PENDING",
            "RESOLVED",
            "CLOSED",
            "REOPENED",
        ):
            result = await client.list_tickets(status=status, page=1, page_size=1)
            count = int(result.get("total", 0))
            if count:
                tickets_by_status[status.lower()] = count
    except TicketServiceError as exc:
        logger.warning("Ticket metrics unavailable: %s", exc)

    return {
        "active_conversations": active_conversations,
        "total_tickets": total_tickets,
        "tickets_by_status": tickets_by_status,
        "agent_runs_today": agent_runs_today,
    }
