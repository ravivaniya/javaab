import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

interface Props {
  children: React.ReactNode;
  /** When true, also require completed onboarding. */
  requireOnboarded?: boolean;
}

/** Gate a route on auth (and optionally onboarding). */
export function RequireAuth({ children, requireOnboarded = true }: Props) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    const search = new URLSearchParams(location.search);
    search.set("redirect", location.pathname);
    return <Navigate to={`/login?${search.toString()}`} replace />;
  }

  if (requireOnboarded && !user.isOnboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
