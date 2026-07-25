package com.multiagent.ticketservice.dto;

import java.util.List;

public record TicketPageResponse(
        List<TicketDetailResponse> tickets,
        long total,
        long page,
        long pageSize
) {
}
