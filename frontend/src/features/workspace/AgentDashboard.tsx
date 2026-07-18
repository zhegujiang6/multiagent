import React, { useEffect, useState, useCallback } from "react";
import {
  MessageSquare,
  Ticket,
  Activity,
  BarChart3,
  ArrowRight,
} from "lucide-react";
import type { DashboardMetrics } from "@/shared/types";

interface AgentDashboardProps {
  onViewTicket: (ticketId: string) => void;
}

const API_BASE = "/api/v1";

export const AgentDashboard: React.FC<AgentDashboardProps> = ({
  onViewTicket,
}) => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/metrics`);
      if (!res.ok) throw new Error("Failed to fetch metrics");
      const data = await res.json();
      setMetrics(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load metrics");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  // ── Loading state ──
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl bg-gray-200"
            />
          ))}
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (error && !metrics) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">{error}</p>
        <button
          onClick={fetchMetrics}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const pendingCount = metrics
    ? (metrics.tickets_by_status["open"] || 0) +
      (metrics.tickets_by_status["in_progress"] || 0)
    : 0;

  const ticketsByStatus = metrics?.tickets_by_status ?? {};

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>

      {/* ── Metrics cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard
          title="Active Conversations"
          value={metrics?.active_conversations ?? 0}
          icon={<MessageSquare className="h-5 w-5" />}
          color="blue"
        />
        <MetricCard
          title="Total Tickets"
          value={metrics?.total_tickets ?? 0}
          icon={<Ticket className="h-5 w-5" />}
          color="purple"
        />
        <MetricCard
          title="Pending"
          value={pendingCount}
          icon={<Activity className="h-5 w-5" />}
          color="yellow"
        />
        <MetricCard
          title="Agent Runs Today"
          value={metrics?.agent_runs_today ?? 0}
          icon={<BarChart3 className="h-5 w-5" />}
          color="green"
        />
      </div>

      {/* ── Tickets by status ── */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          Tickets by Status
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { key: "open", label: "Open", color: "bg-blue-50 text-blue-700" },
            {
              key: "in_progress",
              label: "In Progress",
              color: "bg-purple-50 text-purple-700",
            },
            {
              key: "pending",
              label: "Pending",
              color: "bg-yellow-50 text-yellow-700",
            },
            {
              key: "resolved",
              label: "Resolved",
              color: "bg-green-50 text-green-700",
            },
            {
              key: "closed",
              label: "Closed",
              color: "bg-gray-50 text-gray-600",
            },
          ].map(({ key, label, color }) => (
            <div
              key={key}
              className={`rounded-lg px-4 py-3 text-center ${color}`}
            >
              <p className="text-2xl font-bold">
                {ticketsByStatus[key] ?? 0}
              </p>
              <p className="text-xs font-medium mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Quick actions ── */}
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => onViewTicket("")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            View Ticket Queue
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

// ── MetricCard sub-component ──

interface MetricCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: "blue" | "purple" | "yellow" | "green";
}

const colorMap: Record<
  MetricCardProps["color"],
  { bg: string; iconBg: string; text: string }
> = {
  blue: { bg: "bg-blue-50 border-blue-100", iconBg: "bg-blue-100 text-blue-600", text: "text-blue-900" },
  purple: { bg: "bg-purple-50 border-purple-100", iconBg: "bg-purple-100 text-purple-600", text: "text-purple-900" },
  yellow: { bg: "bg-yellow-50 border-yellow-100", iconBg: "bg-yellow-100 text-yellow-600", text: "text-yellow-900" },
  green: { bg: "bg-green-50 border-green-100", iconBg: "bg-green-100 text-green-600", text: "text-green-900" },
};

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  color,
}) => {
  const c = colorMap[color];
  return (
    <div className={`rounded-xl border p-4 ${c.bg}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600">{title}</span>
        <span className={`rounded-lg p-2 ${c.iconBg}`}>{icon}</span>
      </div>
      <p className={`text-2xl font-bold ${c.text}`}>{value}</p>
    </div>
  );
};

export default AgentDashboard;
