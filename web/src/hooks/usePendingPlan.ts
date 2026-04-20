import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { setPendingPlan, type Plan } from "@/lib/auth";

/**
 * Watch ?plan=plus|pro on any route and stash it in sessionStorage,
 * so post-auth flow can redirect to /subscribe?plan=...
 */
export function usePendingPlan() {
  const [params] = useSearchParams();
  useEffect(() => {
    const p = params.get("plan");
    if (p === "plus" || p === "pro") setPendingPlan(p as Plan);
  }, [params]);
}
