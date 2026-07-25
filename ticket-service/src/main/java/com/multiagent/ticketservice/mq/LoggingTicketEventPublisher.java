package com.multiagent.ticketservice.mq;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
        name = "ticket.events.rocketmq-enabled",
        havingValue = "false",
        matchIfMissing = true
)
public class LoggingTicketEventPublisher implements TicketEventPublisher {

    private static final Logger log = LoggerFactory.getLogger(LoggingTicketEventPublisher.class);

    @Override
    public void publish(String topic, TicketEvent event) {
        log.info("RocketMQ disabled; event topic={} payload={}", topic, event);
    }
}
