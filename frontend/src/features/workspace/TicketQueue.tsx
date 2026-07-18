import React, { useEffect, useState, useCallback } from "react";
import { Search, Filter, AlertCircle, Ticket } from "lucide-react";
import type { TicketSummary } from "@/shared/types";
import { TicketCard } from "@/shared/components/TicketCard";

interface TicketQueueProps {
  onSelectTicket: (ticketId: string) => void;
  selectedId?: string;
}

const API_BASE = "/api/v1";

export const TicketQueue: React.FC<TicketQueueProps> = ({
  onSelectTicket,
  selectedId,
}) => {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");

  const fetchTickets = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      params.set("page", "1");
      params.set("page_size", "50");

      const res = await fetch(`${API_BASE}/tickets?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch tickets");
      const data = await res.json();
      setTickets(data.tickets || []);
      setTotal(data.total || 0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load tickets");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => {
    setIsLoading(true);
    fetchTickets();
  }, [fetchTickets]);

  // Client-side search filter
  const filtered = tickets.filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      t.title.toLowerCase().includes(q) ||
      t.display_id.toLowerCase().includes(q)
    );
  });

  // Check for overdue SLA
  const isOverdue = (ticket: TicketSummary) => {
    if (!ticket.sla_deadline) return false;
    return new Date(ticket.sla_deadline).getTime() < Date.now();
  };

  const isApproachingSLA = (ticket: TicketSummary) => {
    if (!ticket.sla_deadline) return false;
    const remaining = new Date(ticket.sla_deadline).getTime() - Date.now();
    const oneHour = 60 * 60 * 1000;
    return remaining > 0 && remaining < oneHour;
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── Filters ── */}
      <div className="p-3 border-b space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by title or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-1.5 pl-8 pr-3 text-sm
                       focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Filter className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-1.5 pl-7 pr-2 text-xs bg-white
                         focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="pending">Pending</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="relative flex-1">
            <Filter className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-1.5 pl-7 pr-2 text-xs bg-white
                         focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── Ticket list ── */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-thin">
        {/* Loading state */}
        {isLoading && (
          <div className="space-y-2 p-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-24 animate-pulse rounded-lg bg-gray-100"
              />
            ))}
          </div>
        )}

        {/* Error state */}
        {!isLoading && error && (
          <div className="text-center py-8">
            <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-2" />
            <p className="text-sm text-red-500 mb-3">{error}</p>
            <button
              onClick={fetchTickets}
              className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && filtered.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            <Ticket className="mx-auto h-8 w-8 text-gray-300 mb-2" />
            <p className="text-sm">No tickets found</p>
            {(search || statusFilter || priorityFilter) && (
              <p className="text-xs mt-1">Try adjusting your filters</p>
            )}
          </div>
        )}

        {/* Ticket cards */}
        {!isLoading &&
          !error &&
          filtered.map((ticket) => (
            <div
              key={ticket.id}
              className={`relative ${
                selectedId === ticket.id
                  ? "ring-2 ring-primary-500 rounded-lg"
                  : ""
              }`}
            >
              {isOverdue(ticket) && (
                <span className="absolute -top-1 -right-1 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                  !
                </span>
              )}
              {!isOverdue(ticket) && isApproachingSLA(ticket) && (
                <span className="absolute -top-1 -right-1 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-yellow-500 text-[10px] font-bold text-white">
                  !
                </span>
              )}
              <TicketCard
                ticket={ticket}
                onClick={() => onSelectTicket(ticket.id)}
                compact
              />
            </div>
          ))}

        {/* Total count */}
        {!isLoading && !error && total > 0 && (
          <p className="text-center text-xs text-gray-400 py-2">
            Showing {filtered.length} of {total} tickets
          </p>
        )}
      </div>
    </div>
  );
};

export default TicketQueue;
