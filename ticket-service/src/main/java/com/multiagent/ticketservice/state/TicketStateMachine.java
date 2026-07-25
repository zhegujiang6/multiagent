package com.multiagent.ticketservice.state;

import com.multiagent.ticketservice.exception.InvalidStatusTransitionException;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

@Component
public class TicketStateMachine {

    private static final Map<TicketStatus, Set<TicketStatus>> TRANSITIONS =
            new EnumMap<>(TicketStatus.class);

    static {
        TRANSITIONS.put(TicketStatus.NEW, EnumSet.of(TicketStatus.ASSIGNED));
        TRANSITIONS.put(TicketStatus.ASSIGNED, EnumSet.of(TicketStatus.IN_PROGRESS));
        TRANSITIONS.put(
                TicketStatus.IN_PROGRESS,
                EnumSet.of(TicketStatus.PENDING, TicketStatus.RESOLVED)
        );
        TRANSITIONS.put(TicketStatus.PENDING, EnumSet.of(TicketStatus.IN_PROGRESS));
        TRANSITIONS.put(
                TicketStatus.RESOLVED,
                EnumSet.of(TicketStatus.CLOSED, TicketStatus.REOPENED)
        );
        TRANSITIONS.put(TicketStatus.CLOSED, EnumSet.of(TicketStatus.REOPENED));
        TRANSITIONS.put(TicketStatus.REOPENED, EnumSet.of(TicketStatus.IN_PROGRESS));
    }

    public boolean canTransition(TicketStatus from, TicketStatus to) {
        return TRANSITIONS.getOrDefault(from, Set.of()).contains(to);
    }

    public void validate(TicketStatus from, TicketStatus to) {
        if (!canTransition(from, to)) {
            throw new InvalidStatusTransitionException(from, to);
        }
    }
}
