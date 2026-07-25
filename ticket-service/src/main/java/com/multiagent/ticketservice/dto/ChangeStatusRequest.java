package com.multiagent.ticketservice.dto;

import com.multiagent.ticketservice.state.TicketStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ChangeStatusRequest(
        @NotNull TicketStatus status,
        @NotBlank @Size(max = 100) String operatorId,
        @Size(max = 1000) String reason
) {
}
