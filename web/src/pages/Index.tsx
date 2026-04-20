import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { usePendingPlan } from "@/hooks/usePendingPlan";

/** Root: route based on auth state. */
const Index = () => {
  usePendingPlan();
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!user.isOnboarded) return <Navigate to="/onboarding" replace />;
  return <Navigate to="/chat" replace />;
};

export default Index;
