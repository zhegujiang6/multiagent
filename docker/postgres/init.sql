-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Conversations & Messages
-- ============================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL DEFAULT 'web',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    sentiment_trend JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'agent', 'system')),
    content TEXT NOT NULL,
    content_type VARCHAR(30) DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_conv ON messages(conversation_id, created_at);

-- ============================================
-- Users (Customers)
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    tier VARCHAR(30) DEFAULT 'standard' CHECK (tier IN ('vip', 'premium', 'standard')),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- Tickets & Ticket Events
-- ============================================

CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_id VARCHAR(20) UNIQUE NOT NULL,
    conversation_id UUID REFERENCES conversations(id),
    customer_id UUID REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    priority VARCHAR(10) NOT NULL DEFAULT 'P3' CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
    status VARCHAR(30) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'assigned', 'in_progress', 'pending', 'waiting', 'resolved', 'closed', 'reopened')),
    assigned_to VARCHAR(255),
    assigned_dept VARCHAR(100),
    sla_deadline TIMESTAMPTZ,
    sla_response_deadline TIMESTAMPTZ,
    sla_warning_sent BOOLEAN DEFAULT false,
    sla_escalated BOOLEAN DEFAULT false,
    resolution TEXT,
    parent_ticket_id UUID REFERENCES tickets(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_assignee ON tickets(assigned_to);
CREATE INDEX idx_tickets_sla ON tickets(sla_deadline);

CREATE TABLE ticket_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    triggered_by VARCHAR(50) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ticket_events_ticket ON ticket_events(ticket_id, created_at);

-- ============================================
-- Knowledge Base
-- ============================================

CREATE TABLE knowledge_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags JSONB DEFAULT '[]',
    source_ticket_id UUID REFERENCES tickets(id),
    status VARCHAR(30) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'published', 'deprecated', 'approved', 'rejected', 'gap')),
    effectiveness_score FLOAT DEFAULT 0,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- Agent Run Logs (Observability)
-- ============================================

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    agent_name VARCHAR(100) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    latency_ms INT,
    tokens_used INT,
    model_used VARCHAR(100),
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_agent_runs_conv ON agent_runs(conversation_id);
CREATE INDEX idx_agent_runs_name ON agent_runs(agent_name);

-- ============================================
-- Seed: Demo users
-- ============================================

INSERT INTO users (id, external_id, name, email, phone, tier, tags) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'CUST-001', '张伟', 'zhangwei@example.com', '13800001001', 'vip', '["高价值", "产品早期用户"]'),
    ('a0000000-0000-0000-0000-000000000002', 'CUST-002', '李娜', 'lina@example.com', '13800001002', 'premium', '["经常投诉"]'),
    ('a0000000-0000-0000-0000-000000000003', 'CUST-003', '王磊', 'wanglei@example.com', '13800001003', 'standard', '[]');
