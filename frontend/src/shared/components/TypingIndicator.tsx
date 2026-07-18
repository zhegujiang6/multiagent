import React from "react";

export const TypingIndicator: React.FC = () => (
  <div className="flex items-center gap-2 px-4 py-2">
    <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2.5">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      <span className="text-sm text-gray-500">AI is thinking...</span>
    </div>
  </div>
);

export default TypingIndicator;
