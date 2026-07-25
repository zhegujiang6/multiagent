package com.multiagent.ticketservice.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.multiagent.ticketservice.entity.Ticket;
import com.multiagent.ticketservice.mapper.TicketMapper;
import com.multiagent.ticketservice.mq.TicketEvent;
import com.multiagent.ticketservice.mq.TicketEventPublisher;
import com.multiagent.ticketservice.state.TicketStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;

@Component
public class SlaOverdueScheduler {

    private static final Logger log = LoggerFactory.getLogger(SlaOverdueScheduler.class);
    private static final String OVERDUE_KEY_PREFIX = "ticket:sla:overdue:";

    private final TicketMapper ticketMapper;
    private final StringRedisTemplate redisTemplate;
    private final TicketEventPublisher eventPublisher;

    public SlaOverdueScheduler(
            TicketMapper ticketMapper,
            StringRedisTemplate redisTemplate,
            TicketEventPublisher eventPublisher
    ) {
        this.ticketMapper = ticketMapper;
        this.redisTemplate = redisTemplate;
        this.eventPublisher = eventPublisher;
    }

    @Scheduled(fixedDelayString = "${ticket.sla.scan-delay-ms:60000}")
    public void publishOverdueEvents() {
        try {
            List<Ticket> overdueTickets = ticketMapper.selectList(
                    new LambdaQueryWrapper<Ticket>()
                            .le(Ticket::getDeadline, OffsetDateTime.now(ZoneOffset.UTC))
                            .notIn(Ticket::getStatus, TicketStatus.RESOLVED, TicketStatus.CLOSED)
            );
            for (Ticket ticket : overdueTickets) {
                String key = OVERDUE_KEY_PREFIX + ticket.getId();
                Boolean firstNotification = redisTemplate.opsForValue()
                        .setIfAbsent(key, "published", Duration.ofDays(7));
                if (Boolean.TRUE.equals(firstNotification)) {
                    eventPublisher.publish("ticket.sla.overdue", TicketEvent.slaOverdue(ticket));
                }
            }
        } catch (RuntimeException exception) {
            log.warn("Unable to scan overdue tickets", exception);
        }
    }
}
