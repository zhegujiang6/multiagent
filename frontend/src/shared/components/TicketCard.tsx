import React from "react";
import { Ticket } from "lucide-react";
import type { TicketSummary } from "@/shared/types";
import { PriorityBadge } from "./PriorityBadge";
import { SLAIndicator } from "./SLAIndicator";

interface TicketCardProps {
  ticket: TicketSummary;
  onClick?: () => void;
  compact?: boolean;
}

const STATUS_CONFIG: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  open: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    label: "Open",
  },
  in_progress: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    label: "In Progress",
  },
  pending: {
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    label: "Pending",
  },
  resolved: {
    bg: "bg-green-50",
    text: "text-green-700",
    label: "Resolved",
  },
  closed: {
    bg: "bg-gray-50",
    text: "text-gray-600",
    label: "Closed",
  },
};

export const TicketCard: React.FC<TicketCardProps> = ({
  ticket,
  onClick,
  compact = false,
}) => {
  const statusConfig = STATUS_CONFIG[ticket.status] ?? STATUS_CONFIG.open;

  return (
    <div
      className={`group cursor-pointer rounded-lg border border-gray-200 bg-white transition-all hover:border-primary-300 hover:shadow-sm ${
        compact ? "p-2" : "p-3"
      }`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      tabIndex={0}
      role="button"
      aria-label={`Ticket ${ticket.display_id}: ${ticket.title}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Ticket className="h-4 w-4 flex-shrink-0 text-gray-400" />
          <span className="font-mono text-xs text-gray-500">
            {ticket.display_id}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${statusConfig.bg} ${statusConfig.text}`}
          >
            {statusConfig.label}
          </span>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <PriorityBadge priority={ticket.priority} />
        </div>
      </div>

      <h4
        className={`mt-1.5 line-clamp-2 font-medium text-gray-900 group-hover:text-primary-700 ${
          compact ? "text-xs" : "text-sm"
        }`}
      >
        {ticket.title}
      </h4>

      <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
        {ticket.category && (
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px]">
            {ticket.category}
          </span>
        )}
        {ticket.assigned_to && (
          <span className="truncate">Assigned: {ticket.assigned_to}</span>
        )}
      </div>

      {ticket.sla_deadline && (
        <div className="mt-2">
          <SLAIndicator
            deadline={ticket.sla_deadline}
            warning_sent={false}
            escalated={false}
          />
        </div>
      )}
    </div>
  );
};

export default TicketCard;
