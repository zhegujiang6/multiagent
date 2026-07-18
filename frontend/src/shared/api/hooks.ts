import { useState, useCallback, useEffect, useRef } from "react";
import type {
  Message,
  TicketSummary,
  TicketDetail,
  DashboardMetrics,
  TicketFilters,
  UpdateTicketPayload,
  SendMessagePayload,
  KnowledgeArticle,
  KnowledgeArticleListResponse,
  ExtractKnowledgeResponse,
} from "../types";

/* ── Generic fetch wrapper ─────────────────────────────── */

async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as Record<string, string>)?.detail ??
        `Request failed with status ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as Record<string, string>)?.detail ?? `Request failed`,
    );
  }
  return res.json() as Promise<T>;
}

async function apiPatch<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as Record<string, string>)?.detail ?? `Request failed`,
    );
  }
  return res.json() as Promise<T>;
}

/* ── Generic API call hook ─────────────────────────────── */

interface UseApiCallReturn<T, Args extends unknown[]> {
  execute: (...args: Args) => Promise<T | null>;
  data: T | null;
  loading: boolean;
  error: string | null;
  reset: () => void;
}

function useApiCall<T, Args extends unknown[]>(
  fn: (...args: Args) => Promise<T>,
): UseApiCallReturn<T, Args> {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: string | null;
  }>({ data: null, loading: false, error: null });

  // Use a ref to avoid fn changing causing execute to change
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const execute = useCallback(
    async (...args: Args): Promise<T | null> => {
      setState({ data: null, loading: true, error: null });
      try {
        const result = await fnRef.current(...args);
        setState({ data: result, loading: false, error: null });
        return result;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred";
        setState({ data: null, loading: false, error: message });
        return null;
      }
    },
    [], // stable — fn is stored in ref
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

/* ── useCreateConversation ─────────────────────────────── */

interface CreateConversationResponse {
  id: string;
  conversation_id?: string;
}

interface UseCreateConversationReturn {
  createConversation: (customerId?: string, channel?: string) => Promise<string | null>;
  loading: boolean;
  error: string | null;
}

export function useCreateConversation(): UseCreateConversationReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createConversation = useCallback(
    async (customerId = "anonymous", channel = "web"): Promise<string | null> => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiPost<CreateConversationResponse>(
          "/api/v1/conversations",
          { customer_id: customerId, channel },
        );
        return data.conversation_id ?? data.id ?? null;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create conversation";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { createConversation, loading, error };
}

/* ── useSendMessage ────────────────────────────────────── */

interface SendMessageResponse {
  conversation_id: string;
  message: Message;
  agent_statuses: unknown[];
  ticket_created: unknown;
  escalated: boolean;
}

/**
 * Returns a generic execute-based API for sending messages.
 * Call `execute(conversationId, payload)` to send.
 */
export function useSendMessage(): UseApiCallReturn<
  SendMessageResponse,
  [string, SendMessagePayload]
> {
  return useApiCall(
    (conversationId: string, payload: SendMessagePayload) =>
      apiPost<SendMessageResponse>(
        `/api/v1/conversations/${conversationId}/messages`,
        payload,
      ),
  );
}

/* ── useMessages ───────────────────────────────────────── */

interface MessagesResponse {
  messages: Message[];
  total: number;
}

interface UseMessagesReturn {
  messages: Message[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMessages(
  conversationId: string | null,
): UseMessagesReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchMessages = useCallback(async () => {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<MessagesResponse>(
        `/api/v1/conversations/${conversationId}/messages?limit=100`,
      );
      setMessages(data.messages ?? []);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const message =
        err instanceof Error ? err.message : "Failed to fetch messages";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    fetchMessages();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [fetchMessages]);

  return { messages, loading, error, refetch: fetchMessages };
}

/* ── useTickets ────────────────────────────────────────── */

interface TicketsResponse {
  tickets: TicketSummary[];
  total: number;
}

interface UseTicketsReturn {
  tickets: TicketSummary[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTickets(
  filters?: TicketFilters,
): UseTicketsReturn {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filtersKey = JSON.stringify(filters ?? {});

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const sp = new URLSearchParams();
      if (filters?.status) sp.set("status", filters.status);
      if (filters?.priority) sp.set("priority", filters.priority);
      if (filters?.assigned_to) sp.set("assigned_to", filters.assigned_to);
      if (filters?.page) sp.set("page", String(filters.page));
      if (filters?.page_size) sp.set("page_size", String(filters.page_size));

      const qs = sp.toString();
      const url = `/api/v1/tickets${qs ? `?${qs}` : ""}`;
      const data = await apiGet<TicketsResponse>(url);
      setTickets(data.tickets ?? []);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch tickets";
      setError(message);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  return { tickets, loading, error, refetch: fetchTickets };
}

/* ── useTicket ─────────────────────────────────────────── */

interface UseTicketReturn {
  ticket: TicketDetail | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTicket(id: string | null): UseTicketReturn {
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTicket = useCallback(async () => {
    if (!id) {
      setTicket(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<TicketDetail>(`/api/v1/tickets/${id}`);
      setTicket(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch ticket";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTicket();
  }, [fetchTicket]);

  return { ticket, loading, error, refetch: fetchTicket };
}

/* ── useUpdateTicket ───────────────────────────────────── */

interface UseUpdateTicketReturn {
  updateTicket: (
    ticketId: string,
    payload: UpdateTicketPayload,
  ) => Promise<TicketDetail | null>;
  loading: boolean;
  error: string | null;
}

export function useUpdateTicket(): UseUpdateTicketReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateTicket = useCallback(
    async (
      ticketId: string,
      payload: UpdateTicketPayload,
    ): Promise<TicketDetail | null> => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiPatch<TicketDetail>(
          `/api/v1/tickets/${ticketId}`,
          payload,
        );
        return data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to update ticket";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { updateTicket, loading, error };
}

/* ── useMetrics ────────────────────────────────────────── */

interface UseMetricsReturn {
  metrics: DashboardMetrics | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMetrics(): UseMetricsReturn {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<DashboardMetrics>("/api/v1/admin/metrics");
      setMetrics(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch metrics";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { metrics, loading, error, refetch: fetchMetrics };
}

/* ── Knowledge Articles ─────────────────────────────────── */

interface UseKnowledgeArticlesReturn {
  articles: KnowledgeArticle[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useKnowledgeArticles(
  status?: string | null,
): UseKnowledgeArticlesReturn {
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const sp = new URLSearchParams();
      if (status) sp.set("status", status);
      sp.set("page_size", "50");
      const qs = sp.toString();
      const data = await apiGet<KnowledgeArticleListResponse>(
        `/api/v1/knowledge/articles${qs ? `?${qs}` : ""}`,
      );
      setArticles(data.articles ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch knowledge articles";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  return { articles, total, loading, error, refetch: fetchArticles };
}

export function useApproveKnowledgeArticle(): {
  approve: (id: string) => Promise<boolean>;
  loading: boolean;
} {
  const [loading, setLoading] = useState(false);
  const approve = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true);
    try {
      await apiPost(`/api/v1/knowledge/articles/${id}/approve`);
      return true;
    } catch {
      return false;
    } finally {
      setLoading(false);
    }
  }, []);
  return { approve, loading };
}

export function useRejectKnowledgeArticle(): {
  reject: (id: string, reason: string) => Promise<boolean>;
  loading: boolean;
} {
  const [loading, setLoading] = useState(false);
  const reject = useCallback(async (id: string, reason: string): Promise<boolean> => {
    setLoading(true);
    try {
      await apiPost(`/api/v1/knowledge/articles/${id}/reject`, { reason });
      return true;
    } catch {
      return false;
    } finally {
      setLoading(false);
    }
  }, []);
  return { reject, loading };
}

export function useExtractKnowledge(): {
  extract: (conversationId: string) => Promise<ExtractKnowledgeResponse | null>;
  loading: boolean;
} {
  const [loading, setLoading] = useState(false);
  const extract = useCallback(async (conversationId: string) => {
    setLoading(true);
    try {
      return await apiPost<ExtractKnowledgeResponse>(
        `/api/v1/knowledge/extract/${conversationId}/save`,
      );
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  return { extract, loading };
}

/* ── Re-exports for convenience ────────────────────────── */

export { apiGet, apiPost, apiPatch, useApiCall };
