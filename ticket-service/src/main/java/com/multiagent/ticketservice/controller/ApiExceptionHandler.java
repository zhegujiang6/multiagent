package com.multiagent.ticketservice.controller;

import com.multiagent.ticketservice.dto.ApiError;
import com.multiagent.ticketservice.exception.ConcurrentTicketUpdateException;
import com.multiagent.ticketservice.exception.IdempotencyInProgressException;
import com.multiagent.ticketservice.exception.InvalidStatusTransitionException;
import com.multiagent.ticketservice.exception.TicketNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(TicketNotFoundException.class)
    public ResponseEntity<ApiError> notFound(TicketNotFoundException exception) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiError.of("TICKET_NOT_FOUND", exception.getMessage()));
    }

    @ExceptionHandler(InvalidStatusTransitionException.class)
    public ResponseEntity<ApiError> invalidTransition(InvalidStatusTransitionException exception) {
        return ResponseEntity.unprocessableEntity()
                .body(ApiError.of("INVALID_STATUS_TRANSITION", exception.getMessage()));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<ApiError> businessRule(IllegalStateException exception) {
        return ResponseEntity.unprocessableEntity()
                .body(ApiError.of("BUSINESS_RULE_VIOLATION", exception.getMessage()));
    }

    @ExceptionHandler({ConcurrentTicketUpdateException.class, IdempotencyInProgressException.class})
    public ResponseEntity<ApiError> conflict(RuntimeException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ApiError.of("TICKET_CONFLICT", exception.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiError> validation(MethodArgumentNotValidException exception) {
        Map<String, String> errors = new LinkedHashMap<>();
        for (FieldError fieldError : exception.getBindingResult().getFieldErrors()) {
            errors.put(fieldError.getField(), fieldError.getDefaultMessage());
        }
        return ResponseEntity.badRequest().body(
                new ApiError("VALIDATION_FAILED", "Request validation failed", OffsetDateTime.now(), errors)
        );
    }
}
