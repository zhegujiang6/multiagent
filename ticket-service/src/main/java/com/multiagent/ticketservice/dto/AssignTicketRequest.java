package com.multiagent.ticketservice.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AssignTicketRequest(
        @NotBlank @Size(max = 100) String assigneeId,
        @NotBlank @Size(max = 100) String operatorId,
        @Size(max = 1000) String reason
) {
}
