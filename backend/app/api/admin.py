"""Admin API — dashboard metrics and monitoring."""

import logging

from fastapi import APIRouter
from sqlalchemy import select, func

from app.core.database import async_session_factory
from app.models.conversation import Conversation
from app.models.ticket import Ticket
from app.models.agent_run import AgentRun

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

        # Ticket counts by status
        ticket_status_stmt = (
            select(Ticket.status, func.count(Ticket.id))
            .group_by(Ticket.status)
        )
        ticket_rows = (await session.execute(ticket_status_stmt)).all()
        tickets_by_status = {status: count for status, count in ticket_rows}
        total_tickets = sum(tickets_by_status.values())

        # Agent runs today
        today_runs_stmt = select(func.count(AgentRun.id)).where(
            func.date(AgentRun.created_at) == func.current_date()
        )
        agent_runs_today = (await session.execute(today_runs_stmt)).scalar() or 0

    return {
        "active_conversations": active_conversations,
        "total_tickets": total_tickets,
        "tickets_by_status": tickets_by_status,
        "agent_runs_today": agent_runs_today,
    }
