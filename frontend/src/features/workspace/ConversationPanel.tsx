import React, { useEffect, useState } from "react";
import { MessageCircle, ExternalLink } from "lucide-react";
import type { Message } from "@/shared/types";
import { SentimentBadge } from "@/shared/components/SentimentBadge";

interface ConversationPanelProps {
  conversationId: string | null;
}

const API_BASE = "/api/v1";

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  conversationId,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;

    const fetchMessages = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/conversations/${conversationId}/messages`,
        );
        if (!res.ok) throw new Error("Failed to load conversation");
        const data = await res.json();
        if (!cancelled) setMessages(data.messages || []);
      } catch (e: unknown) {
        if (!cancelled)
          setError(
            e instanceof Error ? e.message : "Failed to load messages",
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchMessages();
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  // ── No conversation ──
  if (!conversationId) {
    return (
      <div className="py-6 text-center text-sm text-gray-400">
        <MessageCircle className="mx-auto mb-2 h-6 w-6 text-gray-300" />
        <p>No conversation linked</p>
      </div>
    );
  }

  // ── Loading state ──
  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-12 animate-pulse rounded-lg ${
              i % 2 === 0 ? "ml-8 bg-gray-200" : "mr-8 bg-gray-100"
            }`}
          />
        ))}
      </div>
    );
  }

  // ── Error state ──
  if (error) {
    return (
      <div className="py-4 text-center text-sm text-red-500">{error}</div>
    );
  }

  // ── Empty state ──
  if (messages.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-gray-400">
        No messages in this conversation
      </div>
    );
  }

  return (
    <div className="scrollbar-thin max-h-96 overflow-y-auto space-y-3 rounded-lg border bg-gray-50 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700">
          Conversation
        </h4>
        <a
          href={`/chat?conversation=${conversationId}`}
          className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in full chat
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      {messages.map((msg) => {
        const isCustomer = msg.role === "customer";
        const sentiment = msg.metadata?.sentiment as
          | { label: string; score: number }
          | undefined;

        return (
          <div
            key={msg.id}
            className={`flex ${isCustomer ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                isCustomer
                  ? "bg-primary-600 text-white"
                  : "border bg-white text-gray-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="text-xs opacity-60">
                  {new Date(msg.created_at).toLocaleTimeString()}
                </span>
                {sentiment && (
                  <SentimentBadge
                    label={sentiment.label}
                    score={sentiment.score}
                  />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ConversationPanel;
