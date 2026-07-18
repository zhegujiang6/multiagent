import React from "react";
import { Database } from "lucide-react";
import { Link } from "react-router-dom";
import type { AgentStatus } from "@/shared/types";

interface ChatHeaderProps {
  agentStatuses: AgentStatus[];
  escalated: boolean;
  isConnected: boolean;
}

const AGENT_LABELS: Record<string, string> = {
  intent_classifier: "Analyzing intent...",
  sentiment_analyzer: "Analyzing sentiment...",
  profile_enricher: "Loading customer profile...",
  faq_agent: "Searching knowledge base...",
  ticket_agent: "Creating ticket...",
  orchestrator: "Generating response...",
  intent: "Analyzing intent...",
  sentiment: "Analyzing sentiment...",
  router: "Routing request...",
  ticket: "Creating ticket...",
  response: "Generating response...",
  escalation: "Escalating...",
};

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  agentStatuses,
  escalated,
  isConnected,
}) => {
  const activeAgents = agentStatuses.filter(
    (s) => s.status === "started" || s.status === "in_progress",
  );
  const currentAction =
    activeAgents.length > 0
      ? AGENT_LABELS[activeAgents[0].agent] ||
        `${activeAgents[0].agent} processing...`
      : null;

  return (
    <div className="flex items-center justify-between border-b bg-white px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              escalated
                ? "bg-orange-400 animate-pulse"
                : isConnected
                  ? "bg-green-500"
                  : "bg-gray-400"
            }`}
          />
          <h3 className="font-semibold text-gray-900">
            {escalated ? "Connecting to human agent..." : "Customer Service"}
          </h3>
        </div>
        {currentAction && !escalated && (
          <span className="animate-pulse text-xs text-gray-500">
            {currentAction}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="hidden text-xs text-gray-400 sm:inline">
          {escalated
            ? "Estimated wait 30s"
            : isConnected
              ? "AI Online"
              : "Connecting..."}
        </span>
        <Link
          to="/workspace/knowledge"
          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-gray-700"
          title="打开运营数据中台"
        >
          <Database className="h-3.5 w-3.5" />
          数据中台
        </Link>
      </div>
    </div>
  );
};

export default ChatHeader;
