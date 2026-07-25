package com.multiagent.ticketservice.mq;

import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "ticket.events.rocketmq-enabled", havingValue = "true")
public class RocketMqTicketEventPublisher implements TicketEventPublisher {

    private static final String TICKET_EVENTS_TOPIC = "ticket-events";

    private final RocketMQTemplate rocketMQTemplate;

    public RocketMqTicketEventPublisher(RocketMQTemplate rocketMQTemplate) {
        this.rocketMQTemplate = rocketMQTemplate;
    }

    @Override
    public void publish(String topic, TicketEvent event) {
        // RocketMQ topic names remain infrastructure-oriented; the requested
        // ticket.created/status.changed/sla.overdue names are message tags and
        // are also preserved in eventType.
        rocketMQTemplate.convertAndSend(TICKET_EVENTS_TOPIC + ":" + topic, event);
    }
}
