import React, { useState } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const MAX_CHARS = 5000;

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-white px-4 py-3">
      <div className="flex items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={disabled}
          rows={1}
          maxLength={MAX_CHARS}
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm
                     placeholder-gray-400
                     focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500
                     disabled:cursor-not-allowed disabled:bg-gray-100"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full
                     bg-primary-600 text-white transition-colors
                     hover:bg-primary-700
                     disabled:cursor-not-allowed disabled:bg-gray-300"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-1 flex justify-between">
        <span className="text-xs text-gray-400">
          Enter to send &#183; Shift+Enter for newline
        </span>
        <span
          className={`text-xs ${
            text.length > MAX_CHARS * 0.9 ? "text-red-500" : "text-gray-400"
          }`}
        >
          {text.length}/{MAX_CHARS}
        </span>
      </div>
    </div>
  );
};

export default ChatInput;
