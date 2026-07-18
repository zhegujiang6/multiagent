import React from "react";
import { ExternalLink } from "lucide-react";
import type { TicketSummary } from "@/shared/types";
import { PriorityBadge } from "@/shared/components/PriorityBadge";

interface ChatTicketCardProps {
  ticket: TicketSummary;
  onViewDetails?: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  pending: "Pending",
  resolved: "Resolved",
  closed: "Closed",
};

export const ChatTicketCard: React.FC<ChatTicketCardProps> = ({
  ticket,
  onViewDetails,
}) => {
  const statusLabel = STATUS_LABELS[ticket.status] ?? ticket.status;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-gray-600">
            {ticket.display_id}
          </span>
          <PriorityBadge priority={ticket.priority} />
          <span className="rounded bg-white px-2 py-0.5 text-xs text-gray-600 border">
            {statusLabel}
          </span>
        </div>
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
          >
            View Details
            <ExternalLink className="h-3 w-3" />
          </button>
        )}
      </div>
      <p className="mt-1.5 text-sm font-medium text-gray-900 line-clamp-1">
        {ticket.title}
      </p>
      {ticket.sla_deadline && (
        <p className="mt-1 text-xs text-gray-500">
          Expected response: {new Date(ticket.sla_deadline).toLocaleString()}
        </p>
      )}
    </div>
  );
};

export default ChatTicketCard;
