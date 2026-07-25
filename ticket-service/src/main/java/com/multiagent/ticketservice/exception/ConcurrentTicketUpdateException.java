package com.multiagent.ticketservice.exception;

public class ConcurrentTicketUpdateException extends RuntimeException {

    public ConcurrentTicketUpdateException(Long ticketId) {
        super("Ticket " + ticketId + " was modified concurrently; reload and retry");
    }
}
