import React, { useState, useEffect, useCallback } from "react";
import { Clock } from "lucide-react";

interface SLAIndicatorProps {
  deadline: string | null;
  warning_sent?: boolean;
  escalated?: boolean;
}

function calcRemaining(deadline: string): {
  remainingMs: number;
  percentRemaining: number;
  text: string;
  overdue: boolean;
} {
  const now = Date.now();
  const deadlineTime = new Date(deadline).getTime();
  // Assume a default 24h SLA window
  const totalDuration = 24 * 60 * 60 * 1000;
  const remaining = deadlineTime - now;
  const percent = totalDuration > 0
    ? Math.max(0, Math.min(100, (remaining / totalDuration) * 100))
    : 0;

  const absRemaining = Math.max(0, remaining);
  const hours = Math.floor(absRemaining / (1000 * 60 * 60));
  const minutes = Math.floor((absRemaining % (1000 * 60 * 60)) / (1000 * 60));

  let text: string;
  if (remaining <= 0) {
    text = "Overdue";
  } else if (hours > 0) {
    text = `${hours}h ${minutes}m remaining`;
  } else if (minutes > 0) {
    text = `${minutes}m remaining`;
  } else {
    text = "< 1m remaining";
  }

  return {
    remainingMs: remaining,
    percentRemaining: percent,
    text,
    overdue: remaining <= 0,
  };
}

export const SLAIndicator: React.FC<SLAIndicatorProps> = ({
  deadline,
  warning_sent = false,
  escalated = false,
}) => {
  const [info, setInfo] = useState(() =>
    deadline ? calcRemaining(deadline) : null,
  );

  const tick = useCallback(() => {
    if (deadline) {
      setInfo(calcRemaining(deadline));
    }
  }, [deadline]);

  useEffect(() => {
    tick();
    const interval = setInterval(tick, 30000);
    return () => clearInterval(interval);
  }, [tick]);

  if (!deadline || !info) return null;

  let colorClasses: string;

  if (info.overdue || escalated) {
    colorClasses = "bg-red-50 text-red-700 border-red-200";
  } else if (warning_sent || info.percentRemaining < 25) {
    colorClasses = "bg-yellow-50 text-yellow-700 border-yellow-200";
  } else if (info.percentRemaining > 50) {
    colorClasses = "bg-green-50 text-green-700 border-green-200";
  } else {
    colorClasses = "bg-yellow-50 text-yellow-700 border-yellow-200";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClasses}`}
      title={`SLA deadline: ${new Date(deadline).toLocaleString()}`}
    >
      <Clock className="h-3 w-3" />
      {info.text}
    </span>
  );
};

export default SLAIndicator;
