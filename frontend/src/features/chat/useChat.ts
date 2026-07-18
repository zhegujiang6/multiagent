import { useState, useCallback, useEffect, useRef } from "react";
import { useCustomerServiceStore } from "@/store/customerServiceStore";
import { useSendMessage } from "@/shared/api/hooks";
import type { Message, AgentStatus, WsMessage } from "@/shared/types";
import { useWebSocket } from "./useWebSocket";

const API_BASE = "/api/v1";

export function useChat() {
  const [conversationId, setConversationIdState] = useState<string | null>(null);
  const isConnectedRef = useRef(false);

  // ── Individual Zustand selectors (stable, no full-store re-render) ──
  const messages = useCustomerServiceStore((s) => s.messages);
  const isProcessing = useCustomerServiceStore((s) => s.isProcessing);
  const agentStatuses = useCustomerServiceStore((s) => s.agentStatuses);
  const escalated = useCustomerServiceStore((s) => s.escalated);

  // ── Store actions (stable references from Zustand) ──
  const addMessage = useCustomerServiceStore((s) => s.addMessage);
  const setMessages = useCustomerServiceStore((s) => s.setMessages);
  const setProcessing = useCustomerServiceStore((s) => s.setProcessing);
  const addAgentStatus = useCustomerServiceStore((s) => s.addAgentStatus);
  const setActiveTicket = useCustomerServiceStore((s) => s.setActiveTicket);
  const setConversationIdStore = useCustomerServiceStore((s) => s.setConversationId);

  // ── Store sync helper ──

  const setConversationId = useCallback(
    (id: string | null) => {
      setConversationIdState(id);
      setConversationIdStore(id);
    },
    [setConversationIdStore],
  );

  // ── WebSocket ──

  const {
    lastJsonMessage,
    sendMessage: wsSendMessage,
    readyState,
  } = useWebSocket(conversationId);

  isConnectedRef.current = readyState === WebSocket.OPEN;

  // Process incoming WebSocket messages
  // NOTE: DO NOT put Zustand actions in deps — they are stable references
  useEffect(() => {
    if (!lastJsonMessage) return;
    const data = lastJsonMessage as unknown as WsMessage;

    switch (data.type) {
      case "chat_message": {
        if ("message" in data && data.message) {
          addMessage(data.message as Message);
        }
        setProcessing(false);
        break;
      }
      case "agent_status": {
        addAgentStatus(data as unknown as AgentStatus);
        if (data.status === "started") {
          setProcessing(true);
        }
        break;
      }
      case "ticket_created": {
        setProcessing(false);
        if ("ticket" in data && data.ticket) {
          setActiveTicket(data.ticket as never);
        }
        break;
      }
      case "typing":
        break;
      case "error": {
        setProcessing(false);
        break;
      }
      case "pong":
        break;
      default:
        break;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastJsonMessage]);

  // ── REST API ──

  const sendMessageApi = useSendMessage();

  // ── Load message history ──

  const loadHistory = useCallback(async () => {
    if (!conversationId) return;
    try {
      const res = await fetch(
        `${API_BASE}/conversations/${conversationId}/messages`,
      );
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      }
    } catch {
      // Silently fail - messages will load via WS
    }
  }, [conversationId, setMessages]);

  useEffect(() => {
    if (conversationId) {
      loadHistory();
    }
  }, [conversationId, loadHistory]);

  // ── Send message ──

  const sendMessage = useCallback(
    async (text: string) => {
      if (!conversationId || !text.trim()) return;

      // Add user message optimistically
      const userMsg: Message = {
        id: `temp-${Date.now()}`,
        conversation_id: conversationId,
        role: "customer",
        content: text,
        content_type: "text",
        metadata: {},
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);
      setProcessing(true);

      // Try WebSocket first, fall back to REST
      if (readyState === WebSocket.OPEN) {
        wsSendMessage({ type: "message", payload: { content: text } });
      } else {
        const result = await sendMessageApi.execute(conversationId, {
          content: text.trim(),
          content_type: "text",
        });
        if (result?.message) {
          addMessage(result.message as Message);
        }
        setProcessing(false);
      }
    },
    [conversationId, readyState, wsSendMessage, sendMessageApi, addMessage, setProcessing],
  );

  return {
    messages,
    isProcessing,
    agentStatuses,
    escalated,
    conversationId,
    setConversationId,
    sendMessage,
    isConnected: isConnectedRef.current,
  };
}
