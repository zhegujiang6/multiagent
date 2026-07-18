import { create } from "zustand";
import type {
  Message,
  AgentStatus,
  TicketSummary,
  TicketDetail,
  DashboardMetrics,
} from "@/shared/types";

interface ChatState {
  // ── Conversation ──
  conversationId: string | null;

  // ── Messages ──
  messages: Message[];

  // ── Processing state ──
  isProcessing: boolean;

  // ── Agent statuses ──
  agentStatuses: AgentStatus[];

  // ── Active ticket ──
  activeTicket: TicketSummary | null;

  // ── Escalation ──
  escalated: boolean;

  // ── Ticket list (for agent workspace) ──
  tickets: TicketSummary[];
  totalTickets: number;
  isTicketsLoading: boolean;
  ticketsError: string | null;

  // ── Selected ticket detail (for agent workspace) ──
  selectedTicket: TicketDetail | null;
  isTicketLoading: boolean;
  ticketError: string | null;

  // ── Dashboard metrics (for agent workspace) ──
  dashboardMetrics: DashboardMetrics | null;
  isDashboardLoading: boolean;
  dashboardError: string | null;

  // ── Core Actions ──
  setConversationId: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setProcessing: (processing: boolean) => void;
  addAgentStatus: (status: AgentStatus) => void;
  setActiveTicket: (ticket: TicketSummary | null) => void;
  setEscalated: (escalated: boolean) => void;

  // ── Ticket list actions ──
  setTickets: (tickets: TicketSummary[], total: number) => void;
  setIsTicketsLoading: (loading: boolean) => void;
  setTicketsError: (error: string | null) => void;
  updateTicketInList: (ticket: TicketSummary) => void;

  // ── Ticket detail actions ──
  setSelectedTicket: (ticket: TicketDetail | null) => void;
  setIsTicketLoading: (loading: boolean) => void;
  setTicketError: (error: string | null) => void;

  // ── Dashboard actions ──
  setDashboardMetrics: (metrics: DashboardMetrics | null) => void;
  setIsDashboardLoading: (loading: boolean) => void;
  setDashboardError: (error: string | null) => void;

  // ── Reset ──
  clearAll: () => void;
}

const initialState = {
  conversationId: null as string | null,
  messages: [] as Message[],
  isProcessing: false,
  agentStatuses: [] as AgentStatus[],
  activeTicket: null as TicketSummary | null,
  escalated: false,
  tickets: [] as TicketSummary[],
  totalTickets: 0,
  isTicketsLoading: false,
  ticketsError: null as string | null,
  selectedTicket: null as TicketDetail | null,
  isTicketLoading: false,
  ticketError: null as string | null,
  dashboardMetrics: null as DashboardMetrics | null,
  isDashboardLoading: false,
  dashboardError: null as string | null,
};

export const useCustomerServiceStore = create<ChatState>((set) => ({
  ...initialState,

  // ── Core Actions ──

  setConversationId: (id) => set({ conversationId: id }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setProcessing: (processing) => set({ isProcessing: processing }),

  addAgentStatus: (status) =>
    set((state) => ({
      agentStatuses: [
        ...state.agentStatuses.filter((s) => s.agent !== status.agent),
        status,
      ],
    })),

  setActiveTicket: (ticket) => set({ activeTicket: ticket }),

  setEscalated: (escalated) => set({ escalated }),

  // ── Ticket list actions ──

  setTickets: (tickets, total) =>
    set({ tickets, totalTickets: total }),

  setIsTicketsLoading: (loading) => set({ isTicketsLoading: loading }),

  setTicketsError: (error) => set({ ticketsError: error }),

  updateTicketInList: (updated) =>
    set((state) => ({
      tickets: state.tickets.map((t) =>
        t.id === updated.id ? { ...t, ...updated } : t,
      ),
    })),

  // ── Ticket detail actions ──

  setSelectedTicket: (ticket) => set({ selectedTicket: ticket }),

  setIsTicketLoading: (loading) => set({ isTicketLoading: loading }),

  setTicketError: (error) => set({ ticketError: error }),

  // ── Dashboard actions ──

  setDashboardMetrics: (metrics) => set({ dashboardMetrics: metrics }),

  setIsDashboardLoading: (loading) => set({ isDashboardLoading: loading }),

  setDashboardError: (error) => set({ dashboardError: error }),

  // ── Reset ──

  clearAll: () => set(initialState),
}));
