import React, { useEffect, useState, useCallback } from "react";
import {
  Clock,
  User,
  Tag,
  CheckCircle,
  XCircle,
  AlertCircle,
  PlusCircle,
  ArrowRightCircle,
  RefreshCw,
  MessageCircle,
} from "lucide-react";
import type { TicketDetail as TicketDetailType } from "@/shared/types";
import { PriorityBadge } from "@/shared/components/PriorityBadge";
import { SLAIndicator } from "@/shared/components/SLAIndicator";
import { ConversationPanel } from "./ConversationPanel";

interface TicketDetailProps {
  ticketId: string;
}

const API_BASE = "/api/v1";

const STATUS_LABELS: Record<string, string> = {
  new: "New",
  assigned: "Assigned",
  in_progress: "In Progress",
  pending: "Pending",
  resolved: "Resolved",
  closed: "Closed",
  reopened: "Reopened",
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-indigo-100 text-indigo-800",
  in_progress: "bg-purple-100 text-purple-800",
  pending: "bg-yellow-100 text-yellow-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-600",
  reopened: "bg-orange-100 text-orange-800",
};

const EVENT_ICONS: Record<string, React.ReactNode> = {
  create: <PlusCircle className="h-4 w-4 text-blue-500" />,
  assign: <User className="h-4 w-4 text-purple-500" />,
  resolve: <CheckCircle className="h-4 w-4 text-green-500" />,
  reopen: <RefreshCw className="h-4 w-4 text-orange-500" />,
  comment: <MessageCircle className="h-4 w-4 text-gray-500" />,
  escalate: <AlertCircle className="h-4 w-4 text-red-500" />,
  status_change: <ArrowRightCircle className="h-4 w-4 text-blue-500" />,
};

function getEventIcon(triggeredBy: string, fromStatus: string, toStatus: string): React.ReactNode {
  const key = triggeredBy.toLowerCase();
  if (key.includes("create") || (!fromStatus && toStatus === "new"))
    return EVENT_ICONS.create;
  if (key.includes("assign")) return EVENT_ICONS.assign;
  if (key.includes("resolve") || toStatus === "resolved")
    return EVENT_ICONS.resolve;
  if (key.includes("reopen")) return EVENT_ICONS.reopen;
  if (key.includes("comment")) return EVENT_ICONS.comment;
  if (key.includes("escalat")) return EVENT_ICONS.escalate;
  return EVENT_ICONS.status_change;
}

export const TicketDetail: React.FC<TicketDetailProps> = ({ ticketId }) => {
  const [ticket, setTicket] = useState<TicketDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [showConversation, setShowConversation] = useState(false);

  const fetchTicket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/tickets/${ticketId}`);
      if (!res.ok) throw new Error("Ticket not found");
      setTicket(await res.json());
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to load ticket",
      );
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    fetchTicket();
  }, [fetchTicket]);

  const updateStatus = useCallback(
    async (status: string) => {
      setActionLoading(true);
      try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, comment: comment || undefined }),
        });
        if (res.ok) {
          setTicket(await res.json());
          setComment("");
        }
      } catch {
        // Silently handle
      } finally {
        setActionLoading(false);
      }
    },
    [ticketId, comment],
  );

  const assignTicket = useCallback(async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/${ticketId}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assignee_id: "current-agent",
          operator_id: "current-agent",
          reason: comment || "Claimed from agent workspace",
        }),
      });
      if (res.ok) {
        setTicket(await res.json());
        setComment("");
      }
    } catch {
      // Silently handle
    } finally {
      setActionLoading(false);
    }
  }, [ticketId, comment]);

  // ── Loading state ──
  if (loading) {
    return (
      <div className="animate-fade-in space-y-4">
        <div className="h-8 w-1/3 animate-pulse rounded bg-gray-200" />
        <div className="h-48 animate-pulse rounded-lg bg-gray-200" />
        <div className="h-32 animate-pulse rounded-lg bg-gray-200" />
      </div>
    );
  }

  // ── Error state ──
  if (error || !ticket) {
    return (
      <div className="text-center py-12">
        <XCircle className="mx-auto h-10 w-10 text-red-400 mb-3" />
        <p className="text-red-500 font-medium mb-2">
          {error || "Ticket not found"}
        </p>
        <button
          onClick={fetchTicket}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl animate-fade-in">
      {/* ── Header ── */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="font-mono text-sm text-gray-500">
            {ticket.display_id}
          </span>
          <h1 className="mt-1 text-xl font-bold text-gray-900">
            {ticket.title}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <PriorityBadge priority={ticket.priority} />
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[ticket.status] ?? "bg-gray-100 text-gray-600"}`}
          >
            {STATUS_LABELS[ticket.status] ?? ticket.status}
          </span>
        </div>
      </div>

      {/* ── Info grid ── */}
      <div className="mb-6 grid grid-cols-2 gap-3 rounded-lg bg-gray-50 p-4 text-sm">
        <InfoItem
          icon={<Tag className="h-3.5 w-3.5" />}
          label="Category"
          value={ticket.category || "-"}
        />
        <InfoItem
          icon={<User className="h-3.5 w-3.5" />}
          label="Assigned To"
          value={ticket.assigned_to || "Unassigned"}
        />
        <InfoItem
          icon={<Clock className="h-3.5 w-3.5" />}
          label="Created"
          value={new Date(ticket.created_at).toLocaleString()}
        />
        <InfoItem
          icon={<Clock className="h-3.5 w-3.5" />}
          label="SLA"
          value={
            ticket.sla_deadline ? (
              <SLAIndicator
                deadline={ticket.sla_deadline}
                warning_sent={false}
                escalated={false}
              />
            ) : (
              "N/A"
            )
          }
        />
      </div>

      {/* ── Description ── */}
      <div className="mb-6">
        <h3 className="mb-2 font-semibold text-gray-800">Description</h3>
        <div className="max-h-48 overflow-y-auto rounded-lg border bg-white p-4">
          <p className="whitespace-pre-wrap text-sm text-gray-700">
            {ticket.description || "No description provided."}
          </p>
        </div>
      </div>

      {/* ── Resolution ── */}
      {ticket.resolution && (
        <div className="mb-6">
          <h3 className="mb-2 font-semibold text-green-700">Resolution</h3>
          <div className="rounded-lg border border-green-200 bg-green-50 p-4">
            <p className="whitespace-pre-wrap text-sm text-green-800">
              {ticket.resolution}
            </p>
          </div>
        </div>
      )}

      {/* ── Timeline ── */}
      <div className="mb-6">
        <h3 className="mb-3 font-semibold text-gray-800">Timeline</h3>
        {ticket.events && ticket.events.length > 0 ? (
          <div className="space-y-3">
            {ticket.events.map((event) => {
              const icon =
                getEventIcon(
                  event.triggered_by,
                  event.from_status || "",
                  event.to_status,
                ) ?? EVENT_ICONS.status_change;
              return (
                <div key={event.id} className="flex gap-3 text-sm">
                  <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-100">
                    {icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-gray-700">
                      <span className="text-gray-500">
                        {event.from_status
                          ? `${STATUS_LABELS[event.from_status] ?? event.from_status} → ${STATUS_LABELS[event.to_status] ?? event.to_status}`
                          : (STATUS_LABELS[event.to_status] ?? event.to_status)}
                      </span>
                    </p>
                    {event.comment && (
                      <p className="mt-0.5 text-gray-600">{event.comment}</p>
                    )}
                    <p className="mt-0.5 text-xs text-gray-400">
                      {new Date(event.created_at).toLocaleString()} &middot;{" "}
                      {event.triggered_by}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No events recorded yet.</p>
        )}
      </div>

      {/* ── Conversation panel toggle ── */}
      {ticket.conversation_id && (
        <div className="mb-6">
          <button
            onClick={() => setShowConversation(!showConversation)}
            className="inline-flex items-center gap-2 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            <MessageCircle className="h-4 w-4" />
            {showConversation ? "Hide" : "Show"} Conversation
          </button>
          {showConversation && (
            <div className="mt-3">
              <ConversationPanel
                conversationId={ticket.conversation_id}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Action buttons ── */}
      <div className="border-t pt-4">
        <div className="flex flex-wrap items-center gap-2">
          {ticket.status === "new" && (
            <ActionButton
              label="Claim"
              onClick={assignTicket}
              color="blue"
              loading={actionLoading}
            />
          )}
          {ticket.status === "assigned" && (
            <ActionButton
              label="Start"
              onClick={() => updateStatus("in_progress")}
              color="blue"
              loading={actionLoading}
            />
          )}
          {ticket.status === "in_progress" && (
            <>
              <ActionButton
                label="Resolve"
                onClick={() => updateStatus("resolved")}
                color="green"
                loading={actionLoading}
              />
              <ActionButton
                label="Set Pending"
                onClick={() => updateStatus("pending")}
                color="yellow"
                loading={actionLoading}
              />
            </>
          )}
          {ticket.status === "pending" && (
            <>
              <ActionButton
                label="Resolve"
                onClick={() => updateStatus("resolved")}
                color="green"
                loading={actionLoading}
              />
              <ActionButton
                label="Resume"
                onClick={() => updateStatus("in_progress")}
                color="blue"
                loading={actionLoading}
              />
            </>
          )}
          {ticket.status === "resolved" && (
            <>
              <ActionButton
                label="Close"
                onClick={() => updateStatus("closed")}
                color="green"
                loading={actionLoading}
              />
              <ActionButton
                label="Reopen"
                onClick={() => updateStatus("reopened")}
                color="orange"
                loading={actionLoading}
              />
            </>
          )}
          {ticket.status === "closed" && (
            <ActionButton
              label="Reopen"
              onClick={() => updateStatus("reopened")}
              color="red"
              loading={actionLoading}
            />
          )}
          {ticket.status === "reopened" && (
            <ActionButton
              label="Resume"
              onClick={() => updateStatus("in_progress")}
              color="blue"
              loading={actionLoading}
            />
          )}
        </div>

        {/* ── Comment input ── */}
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Optional reason for the next action..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm
                       focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>
    </div>
  );
};

// ── Sub-components ──

const InfoItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}> = ({ icon, label, value }) => (
  <div className="flex items-start gap-2">
    <span className="mt-0.5 text-gray-400">{icon}</span>
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <div className="font-medium text-gray-800">{value}</div>
    </div>
  </div>
);

const colorClasses: Record<string, string> = {
  blue: "bg-primary-600 hover:bg-primary-700 text-white",
  green: "bg-green-600 hover:bg-green-700 text-white",
  yellow: "bg-yellow-500 hover:bg-yellow-600 text-white",
  orange: "bg-orange-500 hover:bg-orange-600 text-white",
  red: "bg-red-500 hover:bg-red-600 text-white",
};

const ActionButton: React.FC<{
  label: string;
  onClick: () => void;
  color: string;
  loading?: boolean;
}> = ({ label, onClick, color, loading = false }) => (
  <button
    onClick={onClick}
    disabled={loading}
    className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${colorClasses[color] ?? colorClasses.blue}`}
  >
    {loading ? (
      <span className="mr-1.5 h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
    ) : null}
    {label}
  </button>
);

export default TicketDetail;
