package com.multiagent.ticketservice.mq;

import com.multiagent.ticketservice.entity.Ticket;
import com.multiagent.ticketservice.state.TicketStatus;

import java.time.OffsetDateTime;
import java.util.UUID;

public record TicketEvent(
        String eventId,
        String eventType,
        Long ticketId,
        String requestId,
        String conversationId,
        String userId,
        TicketStatus fromStatus,
        TicketStatus toStatus,
        String operatorId,
        String reason,
        OffsetDateTime deadline,
        OffsetDateTime occurredAt
) {
    public static TicketEvent created(Ticket ticket) {
        return new TicketEvent(
                UUID.randomUUID().toString(),
                "ticket.created",
                ticket.getId(),
                ticket.getRequestId(),
                ticket.getConversationId(),
                ticket.getUserId(),
                null,
                TicketStatus.NEW,
                "system",
                "Ticket created",
                ticket.getDeadline(),
                OffsetDateTime.now()
        );
    }

    public static TicketEvent statusChanged(
            Ticket ticket,
            TicketStatus from,
            String operatorId,
            String reason
    ) {
        return new TicketEvent(
                UUID.randomUUID().toString(),
                "ticket.status.changed",
                ticket.getId(),
                ticket.getRequestId(),
                ticket.getConversationId(),
                ticket.getUserId(),
                from,
                ticket.getStatus(),
                operatorId,
                reason,
                ticket.getDeadline(),
                OffsetDateTime.now()
        );
    }

    public static TicketEvent slaOverdue(Ticket ticket) {
        return new TicketEvent(
                UUID.randomUUID().toString(),
                "ticket.sla.overdue",
                ticket.getId(),
                ticket.getRequestId(),
                ticket.getConversationId(),
                ticket.getUserId(),
                ticket.getStatus(),
                ticket.getStatus(),
                "system",
                "Resolution SLA deadline exceeded",
                ticket.getDeadline(),
                OffsetDateTime.now()
        );
    }
}
