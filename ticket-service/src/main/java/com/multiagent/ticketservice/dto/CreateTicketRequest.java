package com.multiagent.ticketservice.dto;

import com.multiagent.ticketservice.state.TicketPriority;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CreateTicketRequest(
        @NotBlank @Size(max = 100) String requestId,
        @NotBlank @Size(max = 100) String conversationId,
        @NotBlank @Size(max = 100) String userId,
        @NotBlank @Size(max = 50) String category,
        @NotNull TicketPriority priority,
        @NotBlank @Size(max = 1000) String summary
) {
}
