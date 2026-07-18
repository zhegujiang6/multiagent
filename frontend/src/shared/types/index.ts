/* ── Core domain types for the Customer Service Multi-Agent system ── */

export interface Conversation {
  id: string;
  customer_id: string;
  channel: string;
  status: "active" | "pending" | "resolved" | "closed";
  sentiment_trend: SentimentTrend | null;
  created_at: string;
  updated_at: string;
}

export interface SentimentTrend {
  direction: "improving" | "declining" | "stable";
  from: number;
  to: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "customer" | "agent" | "system";
  content: string;
  content_type: "text" | "markdown" | "html" | "json";
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Intent {
  label: string;
  confidence: number;
  entities: Record<string, string>;
}

export interface Sentiment {
  label: "positive" | "neutral" | "negative";
  score: number; // -1.0 to 1.0
  triggers: string[];
  trend_assessment: "improving" | "declining" | "stable";
}

/* ── Ticket Models ──────────────────────────────────────── */

export type Priority = "low" | "medium" | "high" | "critical";

export type TicketStatus =
  | "open"
  | "in_progress"
  | "pending"
  | "resolved"
  | "closed";

export interface TicketSummary {
  id: string;
  display_id: string;
  title: string;
  status: TicketStatus;
  priority: Priority;
  category: string;
  sla_deadline: string | null;
  assigned_to: string | null;
  created_at: string;
}

export interface TicketDetail extends TicketSummary {
  description: string;
  resolution: string | null;
  conversation_id: string | null;
  customer_id: string | null;
  events: TicketEvent[];
  updated_at: string;
}

export interface TicketEvent {
  id: string;
  from_status: string;
  to_status: string;
  triggered_by: string;
  comment: string | null;
  created_at: string;
}

/* ── Agent Models ───────────────────────────────────────── */

export interface AgentStatus {
  type: "intent" | "sentiment" | "router" | "ticket" | "response" | "escalation";
  agent: string;
  status: "started" | "in_progress" | "completed" | "failed";
  message: string | null;
  result: Record<string, unknown> | null;
}

/* ── Dashboard Metrics ──────────────────────────────────── */

export interface DashboardMetrics {
  active_conversations: number;
  total_tickets: number;
  tickets_by_status: Record<string, number>;
  agent_runs_today: number;
}

/* ── WebSocket Message Types ────────────────────────────── */

export type WsMessageType =
  | "chat_message"
  | "agent_status"
  | "ticket_created"
  | "ticket_updated"
  | "typing"
  | "error"
  | "pong"
  | "system";

export interface WsMessageBase {
  type: WsMessageType;
}

export interface WsChatMessage extends WsMessageBase {
  type: "chat_message";
  message: Message;
}

export interface WsAgentStatus extends WsMessageBase {
  type: "agent_status";
  agent: string;
  status: "started" | "in_progress" | "completed" | "failed";
  result?: string;
}

export interface WsTicketCreated extends WsMessageBase {
  type: "ticket_created";
  ticket: TicketSummary;
}

export interface WsTicketUpdated extends WsMessageBase {
  type: "ticket_updated";
  ticket: TicketSummary;
}

export interface WsTyping extends WsMessageBase {
  type: "typing";
  is_typing: boolean;
  sender?: string;
}

export interface WsError extends WsMessageBase {
  type: "error";
  message: string;
  code?: string;
}

export interface WsPong extends WsMessageBase {
  type: "pong";
  timestamp: string;
}

export type WsMessage =
  | WsChatMessage
  | WsAgentStatus
  | WsTicketCreated
  | WsTicketUpdated
  | WsTyping
  | WsError
  | WsPong;

/* ── API Payloads ───────────────────────────────────────── */

export interface CreateConversationPayload {
  customer_id?: string;
  channel?: string;
}

export interface SendMessagePayload {
  content: string;
  content_type?: "text" | "markdown" | "html" | "json";
  metadata?: Record<string, unknown>;
}

export interface TicketFilters {
  status?: string;
  priority?: string;
  assigned_to?: string;
  page?: number;
  page_size?: number;
}

export interface UpdateTicketPayload {
  status?: string;
  priority?: string;
  assigned_to?: string;
  title?: string;
  description?: string;
  resolution?: string;
}

/* ── Knowledge Article Models ──────────────────────────────────────── */

export interface KnowledgeArticle {
  id: string;
  title: string;
  content: string;
  category: string | null;
  tags: string[];
  source_ticket_id: string | null;
  source_conversation_id: string | null;
  status: "draft" | "approved" | "rejected" | "gap";
  canonical_key: string;
  content_hash: string;
  source_type: string;
  current_version: number;
  owner: string;
  quality_score: number;
  effectiveness_score: number;
  usage_count: number;
  published_at: string | null;
  retired_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeVersion {
  id: string;
  article_id: string;
  version_number: number;
  title: string;
  content: string;
  content_hash: string;
  change_summary: string | null;
  status: string;
  created_by: string;
  approved_by: string | null;
  created_at: string;
  published_at: string | null;
}

export interface KnowledgeStats {
  total_gaps: number;
  total_articles: number;
  total_approved: number;
  total_drafts: number;
  total_rejected: number;
  total_versions: number;
  total_chunks: number;
  retrievals_24h: number;
  answered_retrievals_24h: number;
  feedback_count: number;
  helpful_rate: number;
  avg_effectiveness: number;
}

export interface KnowledgeArticleListResponse {
  articles: KnowledgeArticle[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExtractKnowledgeResponse {
  conversation_id: string;
  extracted_pairs: Record<string, unknown>[];
  saved_count: number;
}
