import React from "react";
import type { Priority } from "@/shared/types";

interface PriorityBadgeProps {
  priority: Priority;
}

const CONFIG: Record<
  Priority,
  { label: string; bg: string; text: string; dot: string }
> = {
  low: {
    label: "Low",
    bg: "bg-gray-50",
    text: "text-gray-600",
    dot: "bg-gray-400",
  },
  medium: {
    label: "Medium",
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    dot: "bg-yellow-500",
  },
  high: {
    label: "High",
    bg: "bg-orange-50",
    text: "text-orange-700",
    dot: "bg-orange-500",
  },
  critical: {
    label: "Critical",
    bg: "bg-red-50",
    text: "text-red-700",
    dot: "bg-red-500",
  },
};

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  const config = CONFIG[priority] ?? CONFIG.medium;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${config.bg} ${config.text}`}
    >
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
};

export default PriorityBadge;
