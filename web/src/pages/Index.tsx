import { Navigate } from "react-router-dom";
import { widgetConfig } from "@/config/widget.config";

/** Root: redirect to the first enabled feature. */
const Index = () => {
  const { chat, qpg, dpp } = widgetConfig.features;
  if (chat) return <Navigate to="/chat" replace />;
  if (qpg) return <Navigate to="/question-paper" replace />;
  if (dpp) return <Navigate to="/dpp" replace />;
  return <Navigate to="/chat" replace />;
};

export default Index;
