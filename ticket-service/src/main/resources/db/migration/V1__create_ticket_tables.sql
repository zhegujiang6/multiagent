CREATE TABLE IF NOT EXISTS ticket (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL,
    conversation_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    summary VARCHAR(1000) NOT NULL,
    status VARCHAR(30) NOT NULL,
    assignee_id VARCHAR(100),
    deadline TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uk_ticket_request_id UNIQUE (request_id),
    CONSTRAINT ck_ticket_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    CONSTRAINT ck_ticket_status CHECK (
        status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING', 'RESOLVED', 'CLOSED', 'REOPENED')
    )
);

CREATE INDEX IF NOT EXISTS idx_ticket_status_created_at ON ticket(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ticket_assignee_id ON ticket(assignee_id);
CREATE INDEX IF NOT EXISTS idx_ticket_deadline ON ticket(deadline);

CREATE TABLE IF NOT EXISTS ticket_status_log (
    id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    operator_id VARCHAR(100) NOT NULL,
    reason VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ticket_status_log_ticket
    ON ticket_status_log(ticket_id, created_at);
