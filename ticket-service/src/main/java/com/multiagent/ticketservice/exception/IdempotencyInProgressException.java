package com.multiagent.ticketservice.exception;

public class IdempotencyInProgressException extends RuntimeException {

    public IdempotencyInProgressException(String requestId) {
        super("Request " + requestId + " is already being processed");
    }
}
