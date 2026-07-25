package com.multiagent.ticketservice.dto;

import com.multiagent.ticketservice.state.TicketStatus;

import java.time.OffsetDateTime;

public record CreateTicketResponse(
        Long ticketId,
        TicketStatus status,
        OffsetDateTime deadline
) {
}
