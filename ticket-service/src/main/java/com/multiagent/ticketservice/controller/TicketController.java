package com.multiagent.ticketservice.controller;

import com.multiagent.ticketservice.dto.AssignTicketRequest;
import com.multiagent.ticketservice.dto.ChangeStatusRequest;
import com.multiagent.ticketservice.dto.CreateTicketRequest;
import com.multiagent.ticketservice.dto.CreateTicketResponse;
import com.multiagent.ticketservice.dto.TicketDetailResponse;
import com.multiagent.ticketservice.dto.TicketPageResponse;
import com.multiagent.ticketservice.service.TicketService;
import com.multiagent.ticketservice.state.TicketPriority;
import com.multiagent.ticketservice.state.TicketStatus;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.validation.annotation.Validated;

@Validated
@RestController
@RequestMapping("/api/tickets")
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public CreateTicketResponse create(@Valid @RequestBody CreateTicketRequest request) {
        return ticketService.create(request);
    }

    @GetMapping("/{id}")
    public TicketDetailResponse get(@PathVariable Long id) {
        return ticketService.get(id);
    }

    @GetMapping
    public TicketPageResponse list(
            @RequestParam(required = false) TicketStatus status,
            @RequestParam(required = false) TicketPriority priority,
            @RequestParam(required = false) String assigneeId,
            @RequestParam(defaultValue = "1") @Min(1) long page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) long pageSize
    ) {
        return ticketService.list(status, priority, assigneeId, page, pageSize);
    }

    @PatchMapping("/{id}/status")
    public TicketDetailResponse changeStatus(
            @PathVariable Long id,
            @Valid @RequestBody ChangeStatusRequest request
    ) {
        return ticketService.changeStatus(id, request);
    }

    @PostMapping("/{id}/assign")
    public TicketDetailResponse assign(
            @PathVariable Long id,
            @Valid @RequestBody AssignTicketRequest request
    ) {
        return ticketService.assign(id, request);
    }
}
