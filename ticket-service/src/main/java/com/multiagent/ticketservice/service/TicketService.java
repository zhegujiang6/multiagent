package com.multiagent.ticketservice.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.multiagent.ticketservice.dto.AssignTicketRequest;
import com.multiagent.ticketservice.dto.ChangeStatusRequest;
import com.multiagent.ticketservice.dto.CreateTicketRequest;
import com.multiagent.ticketservice.dto.CreateTicketResponse;
import com.multiagent.ticketservice.dto.TicketDetailResponse;
import com.multiagent.ticketservice.dto.TicketPageResponse;
import com.multiagent.ticketservice.dto.TicketStatusLogResponse;
import com.multiagent.ticketservice.entity.Ticket;
import com.multiagent.ticketservice.entity.TicketStatusLog;
import com.multiagent.ticketservice.exception.ConcurrentTicketUpdateException;
import com.multiagent.ticketservice.exception.IdempotencyInProgressException;
import com.multiagent.ticketservice.exception.TicketNotFoundException;
import com.multiagent.ticketservice.mapper.TicketMapper;
import com.multiagent.ticketservice.mapper.TicketStatusLogMapper;
import com.multiagent.ticketservice.mq.TicketEvent;
import com.multiagent.ticketservice.mq.TicketEventPublisher;
import com.multiagent.ticketservice.state.TicketPriority;
import com.multiagent.ticketservice.state.TicketStateMachine;
import com.multiagent.ticketservice.state.TicketStatus;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@Service
public class TicketService {

    private static final String IDEMPOTENCY_PREFIX = "ticket:idempotency:";

    private final TicketMapper ticketMapper;
    private final TicketStatusLogMapper statusLogMapper;
    private final TicketStateMachine stateMachine;
    private final StringRedisTemplate redisTemplate;
    private final TicketEventPublisher eventPublisher;
    private final Duration idempotencyTtl;

    public TicketService(
            TicketMapper ticketMapper,
            TicketStatusLogMapper statusLogMapper,
            TicketStateMachine stateMachine,
            StringRedisTemplate redisTemplate,
            TicketEventPublisher eventPublisher,
            @Value("${ticket.idempotency.ttl:PT24H}") Duration idempotencyTtl
    ) {
        this.ticketMapper = ticketMapper;
        this.statusLogMapper = statusLogMapper;
        this.stateMachine = stateMachine;
        this.redisTemplate = redisTemplate;
        this.eventPublisher = eventPublisher;
        this.idempotencyTtl = idempotencyTtl;
    }

    @Transactional
    public CreateTicketResponse create(CreateTicketRequest request) {
        Ticket existing = ticketMapper.selectByRequestId(request.requestId());
        if (existing != null) {
            return toCreateResponse(existing);
        }

        String redisKey = IDEMPOTENCY_PREFIX + request.requestId();
        String lockToken = UUID.randomUUID().toString();
        Boolean acquired = redisTemplate.opsForValue()
                .setIfAbsent(redisKey, lockToken, idempotencyTtl);
        if (!Boolean.TRUE.equals(acquired)) {
            existing = ticketMapper.selectByRequestId(request.requestId());
            if (existing != null) {
                return toCreateResponse(existing);
            }
            throw new IdempotencyInProgressException(request.requestId());
        }

        try {
            OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
            Ticket ticket = new Ticket();
            ticket.setRequestId(request.requestId());
            ticket.setConversationId(request.conversationId());
            ticket.setUserId(request.userId());
            ticket.setCategory(request.category().trim().toUpperCase(Locale.ROOT));
            ticket.setPriority(request.priority());
            ticket.setSummary(request.summary());
            ticket.setStatus(TicketStatus.NEW);
            ticket.setDeadline(now.plus(request.priority().resolutionSla()));
            ticket.setVersion(0L);
            ticket.setCreatedAt(now);
            ticket.setUpdatedAt(now);
            ticketMapper.insert(ticket);

            insertStatusLog(ticket.getId(), null, TicketStatus.NEW, "system", "Ticket created");
            publishAfterCommit("ticket.created", TicketEvent.created(ticket));
            finalizeIdempotencyKeyAfterCompletion(
                    redisKey,
                    lockToken,
                    ticket.getId().toString()
            );
            return toCreateResponse(ticket);
        } catch (DuplicateKeyException exception) {
            releaseLock(redisKey, lockToken);
            throw new IdempotencyInProgressException(request.requestId());
        } catch (RuntimeException exception) {
            releaseLock(redisKey, lockToken);
            throw exception;
        }
    }

    @Transactional(readOnly = true)
    public TicketDetailResponse get(Long ticketId) {
        Ticket ticket = requireTicket(ticketId);
        return toDetailResponse(ticket, loadLogs(ticketId));
    }

    @Transactional(readOnly = true)
    public TicketPageResponse list(
            TicketStatus status,
            TicketPriority priority,
            String assigneeId,
            long page,
            long pageSize
    ) {
        LambdaQueryWrapper<Ticket> query = new LambdaQueryWrapper<Ticket>()
                .eq(status != null, Ticket::getStatus, status)
                .eq(priority != null, Ticket::getPriority, priority)
                .eq(assigneeId != null && !assigneeId.isBlank(), Ticket::getAssigneeId, assigneeId)
                .orderByDesc(Ticket::getCreatedAt);

        Page<Ticket> result = ticketMapper.selectPage(Page.of(page, pageSize), query);
        List<TicketDetailResponse> tickets = result.getRecords().stream()
                .map(ticket -> TicketDetailResponse.from(ticket, List.of()))
                .toList();
        return new TicketPageResponse(tickets, result.getTotal(), page, pageSize);
    }

    @Transactional
    public TicketDetailResponse changeStatus(Long ticketId, ChangeStatusRequest request) {
        Ticket ticket = requireTicket(ticketId);
        TicketStatus fromStatus = ticket.getStatus();
        stateMachine.validate(fromStatus, request.status());

        ticket.setStatus(request.status());
        ticket.setUpdatedAt(OffsetDateTime.now(ZoneOffset.UTC));
        updateWithOptimisticLock(ticket);
        insertStatusLog(
                ticketId,
                fromStatus,
                request.status(),
                request.operatorId(),
                request.reason()
        );
        publishAfterCommit(
                "ticket.status.changed",
                TicketEvent.statusChanged(ticket, fromStatus, request.operatorId(), request.reason())
        );
        return toDetailResponse(ticket, loadLogs(ticketId));
    }

    @Transactional
    public TicketDetailResponse assign(Long ticketId, AssignTicketRequest request) {
        Ticket ticket = requireTicket(ticketId);
        TicketStatus fromStatus = ticket.getStatus();
        if (fromStatus == TicketStatus.RESOLVED || fromStatus == TicketStatus.CLOSED) {
            throw new IllegalStateException("Resolved or closed tickets cannot be assigned");
        }

        ticket.setAssigneeId(request.assigneeId());
        if (fromStatus == TicketStatus.NEW) {
            stateMachine.validate(fromStatus, TicketStatus.ASSIGNED);
            ticket.setStatus(TicketStatus.ASSIGNED);
        }
        ticket.setUpdatedAt(OffsetDateTime.now(ZoneOffset.UTC));
        updateWithOptimisticLock(ticket);

        if (fromStatus != ticket.getStatus()) {
            insertStatusLog(
                    ticketId,
                    fromStatus,
                    ticket.getStatus(),
                    request.operatorId(),
                    request.reason()
            );
            publishAfterCommit(
                    "ticket.status.changed",
                    TicketEvent.statusChanged(ticket, fromStatus, request.operatorId(), request.reason())
            );
        }
        return toDetailResponse(ticket, loadLogs(ticketId));
    }

    private Ticket requireTicket(Long ticketId) {
        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) {
            throw new TicketNotFoundException(ticketId);
        }
        return ticket;
    }

    private void updateWithOptimisticLock(Ticket ticket) {
        int changed = ticketMapper.updateById(ticket);
        if (changed != 1) {
            throw new ConcurrentTicketUpdateException(ticket.getId());
        }
    }

    private void insertStatusLog(
            Long ticketId,
            TicketStatus fromStatus,
            TicketStatus toStatus,
            String operatorId,
            String reason
    ) {
        TicketStatusLog log = new TicketStatusLog();
        log.setTicketId(ticketId);
        log.setFromStatus(fromStatus);
        log.setToStatus(toStatus);
        log.setOperatorId(operatorId);
        log.setReason(reason);
        log.setCreatedAt(OffsetDateTime.now(ZoneOffset.UTC));
        statusLogMapper.insert(log);
    }

    private List<TicketStatusLogResponse> loadLogs(Long ticketId) {
        return statusLogMapper.selectList(
                        new LambdaQueryWrapper<TicketStatusLog>()
                                .eq(TicketStatusLog::getTicketId, ticketId)
                                .orderByAsc(TicketStatusLog::getCreatedAt)
                ).stream()
                .map(TicketStatusLogResponse::from)
                .toList();
    }

    private TicketDetailResponse toDetailResponse(
            Ticket ticket,
            List<TicketStatusLogResponse> logs
    ) {
        return TicketDetailResponse.from(ticket, logs);
    }

    private CreateTicketResponse toCreateResponse(Ticket ticket) {
        return new CreateTicketResponse(ticket.getId(), ticket.getStatus(), ticket.getDeadline());
    }

    private void publishAfterCommit(String topic, TicketEvent event) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            eventPublisher.publish(topic, event);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                eventPublisher.publish(topic, event);
            }
        });
    }

    private void releaseLock(String key, String expectedValue) {
        redisTemplate.execute(
                new org.springframework.data.redis.core.script.DefaultRedisScript<>(
                        "if redis.call('get', KEYS[1]) == ARGV[1] then "
                                + "return redis.call('del', KEYS[1]) else return 0 end",
                        Long.class
                ),
                List.of(key),
                expectedValue
        );
    }

    private void finalizeIdempotencyKeyAfterCompletion(
            String key,
            String lockToken,
            String ticketId
    ) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            redisTemplate.opsForValue().set(key, ticketId, idempotencyTtl);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                redisTemplate.opsForValue().set(key, ticketId, idempotencyTtl);
            }

            @Override
            public void afterCompletion(int status) {
                if (status != TransactionSynchronization.STATUS_COMMITTED) {
                    releaseLock(key, lockToken);
                }
            }
        });
    }
}
