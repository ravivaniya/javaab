import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

interface Props {
  children: React.ReactNode;
  /** When true, also require completed onboarding. */
  requireOnboarded?: boolean;
  requiredRole?: "student" | "teacher" | "admin";
}

/** Gate a route on auth (and optionally onboarding). */
export function RequireAuth({ children, requireOnboarded = true, requiredRole }: Props) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    const search = new URLSearchParams(location.search);
    search.set("redirect", location.pathname);
    return <Navigate to={`/login?${search.toString()}`} replace />;
  }

  // Check roles primarily so users aren't redirected to onboarding if they failed a role check.
  const currentRole = user.role || "student";
  if (requiredRole && requiredRole !== currentRole) {
    // Basic redirect if not authorized for portal.
    return <Navigate to="/chat" replace />;
  }

  if (requireOnboarded && !user.isOnboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
