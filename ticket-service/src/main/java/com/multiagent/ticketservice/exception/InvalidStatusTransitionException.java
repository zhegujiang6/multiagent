package com.multiagent.ticketservice.exception;

import com.multiagent.ticketservice.state.TicketStatus;

public class InvalidStatusTransitionException extends RuntimeException {

    public InvalidStatusTransitionException(TicketStatus from, TicketStatus to) {
        super("Invalid ticket status transition: " + from + " -> " + to);
    }
}
