import React, { useEffect, useState, useCallback } from "react";
import { ChatHeader } from "./ChatHeader";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { ChatTicketCard } from "./TicketCard";
import { useChat } from "./useChat";
import { useCustomerServiceStore } from "@/store/customerServiceStore";

const API_BASE = "/api/v1";
const VISITOR_ID_KEY = "customer-service-visitor-id";

function getPersistentVisitorId(): string {
  try {
    const existing = window.localStorage.getItem(VISITOR_ID_KEY);
    if (existing) return existing;

    const id = `visitor_${crypto.randomUUID()}`;
    window.localStorage.setItem(VISITOR_ID_KEY, id);
    return id;
  } catch {
    // Privacy-restricted browsers still work, but deliberately do not receive
    // cross-session memory because there is no stable user identity.
    return "anonymous";
  }
}

interface ChatWidgetProps {
  embedded?: boolean;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({
  embedded = false,
}) => {
  const {
    messages,
    isProcessing,
    agentStatuses,
    escalated,
    setConversationId,
    sendMessage,
    isConnected,
  } = useChat();

  const activeTicket = useCustomerServiceStore((s) => s.activeTicket);

  const [error, setError] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [customerId] = useState(getPersistentVisitorId);

  // Create conversation on mount
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      try {
        const res = await fetch(`${API_BASE}/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            customer_id: customerId,
            channel: "web",
          }),
        });
        if (!res.ok) throw new Error("Failed to create conversation");
        const data = await res.json();
        if (!cancelled) {
          setConversationId(data.id);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Connection failed",
          );
        }
      } finally {
        if (!cancelled) setInitializing(false);
      }
    };
    init();
    return () => {
      cancelled = true;
    };
  }, [customerId, setConversationId]);

  const handleRetry = useCallback(() => {
    setError(null);
    setInitializing(true);
    // Re-run init by toggling conversationId
    setConversationId(null);
    setTimeout(() => {
      fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_id: customerId,
          channel: "web",
        }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Failed to create conversation");
          return res.json();
        })
        .then((data) => setConversationId(data.id))
        .catch((e: unknown) =>
          setError(
            e instanceof Error ? e.message : "Connection failed",
          ),
        )
        .finally(() => setInitializing(false));
    }, 100);
  }, [customerId, setConversationId]);

  // Loading state
  if (initializing) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-50 ${
          embedded ? "h-full w-full" : "h-screen"
        }`}
      >
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          <p className="text-gray-500">Connecting to customer service...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-50 ${
          embedded ? "h-full w-full" : "h-screen"
        }`}
      >
        <div className="text-center max-w-sm px-4">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <span className="text-red-500 text-xl">!</span>
          </div>
          <p className="text-red-600 font-medium mb-2">
            Connection failed
          </p>
          <p className="text-sm text-gray-500 mb-4">{error}</p>
          <button
            onClick={handleRetry}
            className="rounded-lg bg-primary-600 px-6 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const containerClass = embedded
    ? "flex flex-col h-full w-full bg-white"
    : "flex flex-col h-screen max-w-2xl mx-auto bg-white shadow-lg";

  return (
    <div className={containerClass}>
      <ChatHeader
        agentStatuses={agentStatuses}
        escalated={escalated}
        isConnected={isConnected}
      />

      {/* Inline ticket card when ticket created */}
      {activeTicket && (
        <div className="px-4 pt-3">
          <ChatTicketCard ticket={activeTicket} />
        </div>
      )}

      <ChatMessages
        messages={messages}
        isProcessing={isProcessing}
        escalated={escalated}
      />

      <ChatInput
        onSend={sendMessage}
        disabled={isProcessing || escalated}
      />
    </div>
  );
};

export default ChatWidget;
