package com.multiagent.ticketservice.dto;

import java.time.OffsetDateTime;
import java.util.Map;

public record ApiError(
        String code,
        String message,
        OffsetDateTime timestamp,
        Map<String, String> fieldErrors
) {
    public static ApiError of(String code, String message) {
        return new ApiError(code, message, OffsetDateTime.now(), Map.of());
    }
}
