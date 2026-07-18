import React from "react";

interface SentimentBadgeProps {
  label: string;
  score: number;
}

const CONFIG: Record<string, { bg: string; text: string; border: string }> = {
  satisfied: {
    bg: "bg-green-50",
    text: "text-green-700",
    border: "border-green-200",
  },
  positive: {
    bg: "bg-green-50",
    text: "text-green-700",
    border: "border-green-200",
  },
  neutral: {
    bg: "bg-gray-50",
    text: "text-gray-600",
    border: "border-gray-200",
  },
  dissatisfied: {
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    border: "border-yellow-200",
  },
  negative: {
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    border: "border-yellow-200",
  },
  angry: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
  },
  desperate: {
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
  },
};

export const SentimentBadge: React.FC<SentimentBadgeProps> = ({
  label,
  score,
}) => {
  const config = CONFIG[label] ?? CONFIG.neutral;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.bg} ${config.text} ${config.border}`}
      title={`Sentiment score: ${score.toFixed(2)}`}
    >
      <span className="capitalize">{label}</span>
      <span className="text-[10px] opacity-60">{score.toFixed(2)}</span>
    </span>
  );
};

export default SentimentBadge;
