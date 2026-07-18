import React, { useEffect, useRef, useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import type { Message } from "@/shared/types";
import { MarkdownRenderer } from "@/shared/components/MarkdownRenderer";
import { SentimentBadge } from "@/shared/components/SentimentBadge";
import { TypingIndicator } from "@/shared/components/TypingIndicator";

interface ChatMessagesProps {
  messages: Message[];
  isProcessing: boolean;
  escalated: boolean;
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  isProcessing,
  escalated,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [feedback, setFeedback] = useState<Record<string, "helpful" | "unhelpful">>({});

  const submitFeedback = async (
    message: Message,
    feedbackType: "helpful" | "unhelpful",
  ) => {
    const retrievalEventId = message.metadata?.retrieval_event_id;
    if (typeof retrievalEventId !== "string" || feedback[message.id]) return;
    setFeedback((current) => ({ ...current, [message.id]: feedbackType }));
    try {
      const response = await fetch("/api/v1/knowledge/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          retrieval_event_id: retrievalEventId,
          conversation_id: message.conversation_id,
          feedback_type: feedbackType,
          score: feedbackType === "helpful" ? 1 : 0,
          source: "chat_widget",
        }),
      });
      if (!response.ok) throw new Error("feedback request failed");
    } catch {
      setFeedback((current) => {
        const next = { ...current };
        delete next[message.id];
        return next;
      });
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  // ── Empty state ──
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="text-center text-gray-400">
          <div className="mb-2 text-4xl">&#128172;</div>
          <p className="text-lg font-medium text-gray-500">
            Hi! How can I help you?
          </p>
          <p className="mt-1 text-sm">
            Ask me anything about your orders, returns, or products.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {messages.map((msg) => {
        const isCustomer = msg.role === "customer";
        const isSystem = msg.role === "system";
        const sentiment = msg.metadata?.sentiment as
          | { label: string; score: number }
          | undefined;
        const retrievalEventId = msg.metadata?.retrieval_event_id;

        // ── System message ──
        if (isSystem) {
          return (
            <div key={msg.id} className="flex justify-center">
              <div className="max-w-md rounded-full bg-gray-100 px-3 py-1 text-center text-xs italic text-gray-500">
                {msg.content}
              </div>
            </div>
          );
        }

        // ── Customer / Agent message ──
        return (
          <div
            key={msg.id}
            className={`flex w-full ${isCustomer ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] break-words rounded-2xl px-4 py-2.5 shadow-sm ${
                isCustomer
                  ? "ml-auto bg-blue-600 text-white rounded-br-md"
                  : "bg-gray-100 text-gray-900 rounded-bl-md"
              }`}
            >
              {isCustomer ? (
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
              ) : (
                <>
                  <MarkdownRenderer content={msg.content} />
                  {sentiment && (
                    <div className="mt-1.5">
                      <SentimentBadge
                        label={sentiment.label}
                        score={sentiment.score}
                      />
                    </div>
                  )}
                  {typeof retrievalEventId === "string" && (
                    <div className="mt-2 flex items-center gap-1 border-t border-gray-200 pt-2 text-gray-400">
                      <span className="mr-1 text-[11px]">这个回答有帮助吗？</span>
                      <button
                        type="button"
                        onClick={() => void submitFeedback(msg, "helpful")}
                        className={`rounded p-1 hover:bg-white hover:text-emerald-600 ${feedback[msg.id] === "helpful" ? "bg-white text-emerald-600" : ""}`}
                        aria-label="有帮助"
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => void submitFeedback(msg, "unhelpful")}
                        className={`rounded p-1 hover:bg-white hover:text-rose-600 ${feedback[msg.id] === "unhelpful" ? "bg-white text-rose-600" : ""}`}
                        aria-label="没有帮助"
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        );
      })}

      {/* ── Typing indicator ── */}
      {isProcessing && <TypingIndicator />}

      {/* ── Escalation system message ── */}
      {escalated && (
        <div className="flex justify-center">
          <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs text-orange-700">
            Transferring to human agent, please wait...
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

export default ChatMessages;
