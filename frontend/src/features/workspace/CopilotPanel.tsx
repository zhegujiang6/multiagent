import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Lightbulb,
  BookOpen,
  Users,
  MessageSquare,
  Shield,
} from "lucide-react";

interface CopilotPanelProps {
  ticketId: string;
}

type SectionKey = "suggested" | "knowledge" | "similar" | "insights";

export const CopilotPanel: React.FC<CopilotPanelProps> = ({ ticketId: _ticketId }) => {
  const [activeSection, setActiveSection] = useState<SectionKey | null>(
    "suggested",
  );

  const toggleSection = (section: SectionKey) => {
    setActiveSection(activeSection === section ? null : section);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="h-5 w-5 text-yellow-500" />
        <h4 className="text-sm font-semibold text-gray-700">
          AI Copilot
        </h4>
      </div>

      {/* ── Suggested Response ── */}
      <CollapsibleSection
        title="Suggested Response"
        section="suggested"
        activeSection={activeSection}
        onToggle={() => toggleSection("suggested")}
        icon={<MessageSquare className="h-4 w-4 text-primary-500" />}
        loading={false}
        isEmpty={false}
      >
        <div className="rounded-lg bg-primary-50 p-3 text-sm">
          <p className="italic text-gray-700">
            "Thank you for reaching out. I understand your concern regarding
            this issue. Based on our review, here is what we recommend..."
          </p>
          <button
            onClick={() => {
              navigator.clipboard.writeText(
                "Thank you for reaching out. I understand your concern regarding this issue. Based on our review, here is what we recommend...",
              );
            }}
            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
          >
            <Copy className="h-3 w-3" />
            Copy to clipboard
          </button>
        </div>
      </CollapsibleSection>

      {/* ── Related Knowledge ── */}
      <CollapsibleSection
        title="Related Knowledge"
        section="knowledge"
        activeSection={activeSection}
        onToggle={() => toggleSection("knowledge")}
        icon={<BookOpen className="h-4 w-4 text-green-500" />}
        loading={false}
        isEmpty={false}
      >
        <div className="space-y-2">
          {[
            { title: "Return Policy", summary: "Standard return policy: 30-day window, original packaging required." },
            { title: "Shipping FAQ", summary: "Domestic shipping: 3-5 business days. International: 7-14 days." },
          ].map((item, i) => (
            <div
              key={i}
              className="rounded-lg border border-gray-200 bg-white p-2.5 hover:shadow-sm transition-shadow cursor-pointer"
            >
              <p className="text-xs font-medium text-gray-800">
                {item.title}
              </p>
              <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
                {item.summary}
              </p>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* ── Similar Tickets ── */}
      <CollapsibleSection
        title="Similar Tickets"
        section="similar"
        activeSection={activeSection}
        onToggle={() => toggleSection("similar")}
        icon={<MessageSquare className="h-4 w-4 text-orange-500" />}
        loading={false}
        isEmpty={false}
      >
        <div className="space-y-2">
          {[
            { id: "TKT-2024-0101", title: "Refund not processed within 5 days", status: "resolved" },
            { id: "TKT-2024-0098", title: "Order #12345 missing item", status: "resolved" },
          ].map((item) => (
            <div
              key={item.id}
              className="rounded-lg border border-gray-200 bg-white p-2.5 hover:shadow-sm transition-shadow cursor-pointer"
            >
              <div className="flex items-center justify-between gap-1">
                <span className="font-mono text-[10px] text-gray-400">
                  {item.id}
                </span>
                <span className="rounded bg-green-50 px-1.5 py-0.5 text-[9px] font-medium text-green-600">
                  {item.status}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-gray-700 line-clamp-1">
                {item.title}
              </p>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* ── Customer Insights ── */}
      <CollapsibleSection
        title="Customer Insights"
        section="insights"
        activeSection={activeSection}
        onToggle={() => toggleSection("insights")}
        icon={<Users className="h-4 w-4 text-purple-500" />}
        loading={false}
        isEmpty={false}
      >
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between rounded bg-gray-50 px-3 py-2">
            <span className="text-gray-500">Tier</span>
            <span className="font-medium text-gray-800">Standard</span>
          </div>
          <div className="flex items-center justify-between rounded bg-gray-50 px-3 py-2">
            <span className="text-gray-500">History</span>
            <span className="font-medium text-gray-800">
              3 conversations
            </span>
          </div>
          <div className="flex items-center justify-between rounded bg-gray-50 px-3 py-2">
            <span className="text-gray-500">Risk Level</span>
            <span className="inline-flex items-center gap-1 font-medium text-green-600">
              <Shield className="h-3 w-3" />
              Low
            </span>
          </div>
          <div className="mt-2">
            <p className="text-gray-500 mb-1">Tags</p>
            <div className="flex flex-wrap gap-1">
              {["return", "refund", "order-issue"].map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
};

// ── CollapsibleSection sub-component ──

interface CollapsibleSectionProps {
  title: string;
  section: SectionKey;
  activeSection: SectionKey | null;
  onToggle: () => void;
  icon: React.ReactNode;
  loading: boolean;
  isEmpty: boolean;
  children: React.ReactNode;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  section,
  activeSection,
  onToggle,
  icon,
  loading,
  isEmpty,
  children,
}) => {
  const isOpen = activeSection === section;

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 bg-gray-50 px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
      >
        <span className="flex items-center gap-2">
          {icon}
          {title}
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {isOpen && (
        <div className="p-3">
          {loading ? (
            <div className="space-y-2">
              <div className="h-8 animate-pulse rounded bg-gray-100" />
              <div className="h-8 animate-pulse rounded bg-gray-100" />
            </div>
          ) : isEmpty ? (
            <p className="text-xs text-gray-400">No data available</p>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
};

export default CopilotPanel;
