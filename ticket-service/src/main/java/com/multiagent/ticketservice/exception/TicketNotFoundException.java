package com.multiagent.ticketservice.exception;

public class TicketNotFoundException extends RuntimeException {

    public TicketNotFoundException(Long ticketId) {
        super("Ticket " + ticketId + " was not found");
    }
}
