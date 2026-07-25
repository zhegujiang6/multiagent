package com.multiagent.ticketservice.state;

import java.time.Duration;

public enum TicketPriority {
    LOW(Duration.ofHours(24)),
    MEDIUM(Duration.ofHours(8)),
    HIGH(Duration.ofHours(4)),
    URGENT(Duration.ofHours(1));

    private final Duration resolutionSla;

    TicketPriority(Duration resolutionSla) {
        this.resolutionSla = resolutionSla;
    }

    public Duration resolutionSla() {
        return resolutionSla;
    }
}
