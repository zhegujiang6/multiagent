import { useEffect, useRef, useState, useCallback } from "react";

// Use relative URL so WS goes through Vite proxy (avoids CORS issues)
const WS_BASE_URL = `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}`;

const HEARTBEAT_INTERVAL_MS = 30_000;
const INITIAL_RECONNECT_DELAY_MS = 1_000;
const MAX_RECONNECT_DELAY_MS = 30_000;
const RECONNECT_MULTIPLIER = 2;

interface UseWebSocketReturn {
  sendMessage: (data: Record<string, unknown>) => void;
  sendTyping: (isTyping: boolean) => void;
  lastJsonMessage: Record<string, unknown> | null;
  readyState: number;
  disconnect: () => void;
}

export function useWebSocket(
  conversationId: string | null,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const mountedRef = useRef(true);
  const intentionalCloseRef = useRef(false);

  const [lastJsonMessage, setLastJsonMessage] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;

    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }

    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setReadyState(WebSocket.CLOSED);
  }, []);

  const connect = useCallback(() => {
    if (!conversationId || !mountedRef.current) return;
    if (intentionalCloseRef.current) return;

    // Close existing connection before opening a new one
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const url = `${WS_BASE_URL}/api/v1/ws/chat?conversation_id=${encodeURIComponent(conversationId)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setReadyState(WebSocket.CONNECTING);

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close();
          return;
        }
        setReadyState(WebSocket.OPEN);
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;

        // Start heartbeat
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data as string) as Record<
            string,
            unknown
          >;
          setLastJsonMessage(data);
        } catch {
          console.warn("[WS] Failed to parse message:", event.data);
        }
      };

      ws.onerror = () => {
        // The onclose handler will fire after this; no-op here
      };

      ws.onclose = (event: CloseEvent) => {
        if (!mountedRef.current) return;
        setReadyState(WebSocket.CLOSED);

        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
          heartbeatRef.current = null;
        }

        // Don't reconnect if intentional or normal closure
        if (intentionalCloseRef.current || event.code === 1000) return;

        // Exponential backoff reconnect
        if (reconnectRef.current) clearTimeout(reconnectRef.current);
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            reconnectDelayRef.current = Math.min(
              reconnectDelayRef.current * RECONNECT_MULTIPLIER,
              MAX_RECONNECT_DELAY_MS,
            );
            connect();
          }
        }, reconnectDelayRef.current);
      };
    } catch {
      // Connection failed, schedule retry
      if (mountedRef.current && !intentionalCloseRef.current) {
        if (reconnectRef.current) clearTimeout(reconnectRef.current);
        reconnectRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(
            reconnectDelayRef.current * RECONNECT_MULTIPLIER,
            MAX_RECONNECT_DELAY_MS,
          );
          connect();
        }, reconnectDelayRef.current);
      }
    }
  }, [conversationId]);

  // Connect / reconnect when conversationId changes
  useEffect(() => {
    mountedRef.current = true;
    intentionalCloseRef.current = false;
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;

    if (conversationId) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const sendTyping = useCallback(
    (isTyping: boolean) => {
      sendMessage({ type: "typing", is_typing: isTyping });
    },
    [sendMessage],
  );

  return {
    sendMessage,
    sendTyping,
    lastJsonMessage,
    readyState,
    disconnect,
  };
}
