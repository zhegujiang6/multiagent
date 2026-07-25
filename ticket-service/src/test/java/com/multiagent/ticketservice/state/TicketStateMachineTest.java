package com.multiagent.ticketservice.state;

import com.multiagent.ticketservice.exception.InvalidStatusTransitionException;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TicketStateMachineTest {

    private final TicketStateMachine stateMachine = new TicketStateMachine();

    @Test
    void allowsExpectedHappyPath() {
        assertTrue(stateMachine.canTransition(TicketStatus.NEW, TicketStatus.ASSIGNED));
        assertTrue(stateMachine.canTransition(TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS));
        assertTrue(stateMachine.canTransition(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED));
        assertTrue(stateMachine.canTransition(TicketStatus.RESOLVED, TicketStatus.CLOSED));
        assertDoesNotThrow(
                () -> stateMachine.validate(TicketStatus.CLOSED, TicketStatus.REOPENED)
        );
    }

    @Test
    void supportsPendingAndReopenedBranches() {
        assertTrue(stateMachine.canTransition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING));
        assertTrue(stateMachine.canTransition(TicketStatus.PENDING, TicketStatus.IN_PROGRESS));
        assertTrue(stateMachine.canTransition(TicketStatus.REOPENED, TicketStatus.IN_PROGRESS));
    }

    @Test
    void rejectsIllegalJumps() {
        assertFalse(stateMachine.canTransition(TicketStatus.ASSIGNED, TicketStatus.CLOSED));
        assertThrows(
                InvalidStatusTransitionException.class,
                () -> stateMachine.validate(TicketStatus.CLOSED, TicketStatus.IN_PROGRESS)
        );
    }
}
