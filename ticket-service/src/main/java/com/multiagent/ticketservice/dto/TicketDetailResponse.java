package com.multiagent.ticketservice.dto;

import com.multiagent.ticketservice.entity.Ticket;
import com.multiagent.ticketservice.state.TicketPriority;
import com.multiagent.ticketservice.state.TicketStatus;

import java.time.OffsetDateTime;
import java.util.List;

public record TicketDetailResponse(
        Long ticketId,
        String requestId,
        String conversationId,
        String userId,
        String category,
        TicketPriority priority,
        String summary,
        TicketStatus status,
        String assigneeId,
        OffsetDateTime deadline,
        Long version,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt,
        List<TicketStatusLogResponse> statusLogs
) {
    public static TicketDetailResponse from(Ticket ticket, List<TicketStatusLogResponse> logs) {
        return new TicketDetailResponse(
                ticket.getId(),
                ticket.getRequestId(),
                ticket.getConversationId(),
                ticket.getUserId(),
                ticket.getCategory(),
                ticket.getPriority(),
                ticket.getSummary(),
                ticket.getStatus(),
                ticket.getAssigneeId(),
                ticket.getDeadline(),
                ticket.getVersion(),
                ticket.getCreatedAt(),
                ticket.getUpdatedAt(),
                logs
        );
    }
}
