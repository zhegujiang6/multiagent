import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, MessageCircle, PanelLeft, X, BookOpen } from "lucide-react";
import { TicketQueue } from "./TicketQueue";
import { TicketDetail } from "./TicketDetail";
import { AgentDashboard } from "./AgentDashboard";
import { KnowledgePanel } from "@/features/knowledge";
import { CopilotPanel } from "./CopilotPanel";

type ViewMode = "dashboard" | "ticket" | "knowledge";
type MobilePanel = "queue" | "main" | "copilot";

interface WorkspaceProps {
  initialView?: ViewMode;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  initialView = "dashboard",
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("queue");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSelectTicket = (ticketId: string) => {
    setSelectedTicketId(ticketId);
    setViewMode("ticket");
    setMobilePanel("main");
  };

  const handleBackToDashboard = () => {
    setViewMode("dashboard");
    setSelectedTicketId(null);
  };

  const renderCenter = () => {
    if (viewMode === "knowledge") {
      return <KnowledgePanel />;
    }
    if (viewMode === "dashboard" || !selectedTicketId) {
      return <AgentDashboard onViewTicket={handleSelectTicket} />;
    }
    return <TicketDetail ticketId={selectedTicketId} />;
  };

  const isCenterVisible = () => {
    if (mobilePanel === "main") return true;
    if (viewMode === "dashboard" || viewMode === "knowledge") return true;
    return false;
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* ── Mobile header ── */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center gap-2 bg-white border-b px-3 py-2">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1.5 rounded hover:bg-gray-100"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5 text-gray-600" />
        </button>
        <div className="flex gap-1">
          {(["queue", "main", "copilot"] as MobilePanel[]).map((p) => (
            <button
              key={p}
              onClick={() => setMobilePanel(p)}
              className={`px-3 py-1 text-xs font-medium rounded ${
                mobilePanel === p
                  ? "bg-primary-100 text-primary-700"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {p === "queue" ? "Queue" : p === "main" ? "Main" : "Copilot"}
            </button>
          ))}
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="ml-auto p-1.5 rounded hover:bg-gray-100 lg:hidden"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      {/* ── Left sidebar ── */}
      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 fixed lg:relative z-20 top-0 lg:top-0 left-0 h-full w-80 flex-shrink-0 border-r bg-white overflow-hidden flex flex-col transition-transform duration-200 pt-12 lg:pt-0 ${
          mobilePanel === "queue" ? "block" : "hidden lg:flex"
        }`}
      >
        {/* Top navigation */}
        <div className="px-4 py-3 border-b space-y-2">
          <Link
            to="/chat"
            className="w-full text-sm font-medium flex items-center gap-2 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
          >
            <MessageCircle className="h-4 w-4" />
            返回客服对话
          </Link>
          <button
            onClick={handleBackToDashboard}
            className="text-sm text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1"
          >
            <PanelLeft className="h-4 w-4" />
            运营工作台
          </button>

          {/* Knowledge data platform button */}
          <button
            onClick={() => setViewMode("knowledge")}
            className={`w-full text-sm font-medium flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              viewMode === "knowledge"
                ? "bg-primary-50 text-primary-700"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <BookOpen className="h-4 w-4" />
            数据中台
          </button>
        </div>

        {viewMode !== "knowledge" && (
          <TicketQueue
            onSelectTicket={handleSelectTicket}
            selectedId={selectedTicketId ?? undefined}
          />
        )}
        {viewMode === "knowledge" && (
          <div className="flex-1 px-4 py-3">
            <p className="text-xs text-gray-400 leading-relaxed">
              统一治理知识资产、版本、切片、检索效果和用户反馈；审核通过后自动发布到 AI 检索索引。
            </p>
          </div>
        )}
      </aside>

      {/* ── Overlay for mobile sidebar ── */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 z-10 bg-black/30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Center ── */}
      <main
        className={`flex-1 overflow-y-auto p-6 pt-14 lg:pt-6 ${
          isCenterVisible() ? "block" : "hidden lg:block"
        }`}
      >
        {renderCenter()}
      </main>

      {/* ── Right sidebar: Copilot ── */}
      {viewMode === "ticket" && selectedTicketId && (
        <aside
          className={`w-72 flex-shrink-0 border-l bg-white overflow-y-auto p-4 ${
            mobilePanel === "copilot" ? "block" : "hidden lg:block"
          }`}
        >
          <CopilotPanel ticketId={selectedTicketId} />
        </aside>
      )}
    </div>
  );
};

export default Workspace;
