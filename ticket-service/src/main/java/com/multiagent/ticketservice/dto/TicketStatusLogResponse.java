package com.multiagent.ticketservice.dto;

import com.multiagent.ticketservice.entity.TicketStatusLog;
import com.multiagent.ticketservice.state.TicketStatus;

import java.time.OffsetDateTime;

public record TicketStatusLogResponse(
        Long id,
        TicketStatus fromStatus,
        TicketStatus toStatus,
        String operatorId,
        String reason,
        OffsetDateTime createdAt
) {
    public static TicketStatusLogResponse from(TicketStatusLog log) {
        return new TicketStatusLogResponse(
                log.getId(),
                log.getFromStatus(),
                log.getToStatus(),
                log.getOperatorId(),
                log.getReason(),
                log.getCreatedAt()
        );
    }
}
