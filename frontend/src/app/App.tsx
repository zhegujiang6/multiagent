import { Routes, Route, Navigate } from "react-router-dom";
import { ChatWidget } from "@/features/chat";
import { Workspace } from "@/features/workspace";
import { ErrorBoundary } from "@/shared/components/ErrorBoundary";

function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50">
      <ErrorBoundary>
        <Routes>
          <Route path="/chat" element={<ChatWidget />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route
            path="/workspace/knowledge"
            element={<Workspace initialView="knowledge" />}
          />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
}

export default App;
