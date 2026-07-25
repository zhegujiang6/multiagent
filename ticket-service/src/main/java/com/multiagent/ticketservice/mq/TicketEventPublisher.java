package com.multiagent.ticketservice.mq;

public interface TicketEventPublisher {

    void publish(String topic, TicketEvent event);
}
