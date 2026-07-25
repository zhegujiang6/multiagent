package com.multiagent.ticketservice.service;

import com.multiagent.ticketservice.dto.CreateTicketRequest;
import com.multiagent.ticketservice.dto.CreateTicketResponse;
import com.multiagent.ticketservice.entity.Ticket;
import com.multiagent.ticketservice.entity.TicketStatusLog;
import com.multiagent.ticketservice.mapper.TicketMapper;
import com.multiagent.ticketservice.mapper.TicketStatusLogMapper;
import com.multiagent.ticketservice.mq.TicketEventPublisher;
import com.multiagent.ticketservice.mq.TicketEvent;
import com.multiagent.ticketservice.state.TicketPriority;
import com.multiagent.ticketservice.state.TicketStateMachine;
import com.multiagent.ticketservice.state.TicketStatus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.time.OffsetDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TicketServiceTest {

    @Mock
    private TicketMapper ticketMapper;
    @Mock
    private TicketStatusLogMapper statusLogMapper;
    @Mock
    private StringRedisTemplate redisTemplate;
    @Mock
    private ValueOperations<String, String> valueOperations;
    @Mock
    private TicketEventPublisher eventPublisher;

    @Test
    void returnsExistingTicketBeforeTakingRedisLock() {
        Ticket existing = new Ticket();
        existing.setId(10001L);
        existing.setRequestId("req-1");
        existing.setStatus(TicketStatus.NEW);
        existing.setDeadline(OffsetDateTime.parse("2026-07-25T18:00:00+08:00"));
        when(ticketMapper.selectByRequestId("req-1")).thenReturn(existing);

        TicketService service = new TicketService(
                ticketMapper,
                statusLogMapper,
                new TicketStateMachine(),
                redisTemplate,
                eventPublisher,
                Duration.ofHours(24)
        );
        CreateTicketResponse response = service.create(new CreateTicketRequest(
                "req-1",
                "conv-1",
                "user-1",
                "REFUND",
                TicketPriority.HIGH,
                "Refund requested"
        ));

        assertEquals(10001L, response.ticketId());
        assertEquals(TicketStatus.NEW, response.status());
        verify(redisTemplate, never()).opsForValue();
        verify(ticketMapper, never()).insert(existing);
    }

    @Test
    void createsTicketAfterAcquiringRedisIdempotencyKey() {
        when(ticketMapper.selectByRequestId("req-new")).thenReturn(null);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.setIfAbsent(
                eq("ticket:idempotency:req-new"),
                any(String.class),
                eq(Duration.ofHours(24))
        )).thenReturn(true);
        doAnswer(invocation -> {
            Ticket ticket = invocation.getArgument(0);
            ticket.setId(10002L);
            return 1;
        }).when(ticketMapper).insert(any(Ticket.class));

        TicketService service = new TicketService(
                ticketMapper,
                statusLogMapper,
                new TicketStateMachine(),
                redisTemplate,
                eventPublisher,
                Duration.ofHours(24)
        );
        CreateTicketResponse response = service.create(new CreateTicketRequest(
                "req-new",
                "conv-1",
                "user-1",
                "REFUND",
                TicketPriority.HIGH,
                "Refund requested"
        ));

        assertEquals(10002L, response.ticketId());
        assertEquals(TicketStatus.NEW, response.status());
        verify(statusLogMapper).insert(any(TicketStatusLog.class));
        verify(eventPublisher).publish(eq("ticket.created"), any(TicketEvent.class));
        verify(valueOperations).set(
                "ticket:idempotency:req-new",
                "10002",
                Duration.ofHours(24)
        );
    }
}
