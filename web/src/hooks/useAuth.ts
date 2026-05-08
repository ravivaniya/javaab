import { useCallback, useEffect, useState } from "react";
import {
  clearUser,
  getUser,
  JavaabUser,
  saveProfileCache,
  setUser,
} from "@/lib/auth";
import { ApiService } from "@/services/api";

/** Reactive auth state hook. */
export function useAuth() {
  const [user, setUserState] = useState<JavaabUser | null>(() => getUser());

  useEffect(() => {
    const sync = () => setUserState(getUser());
    window.addEventListener("javaab:auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("javaab:auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const updateUser = useCallback(async (patch: Partial<JavaabUser>) => {
    const cur = getUser();
    if (!cur) return;
    const next = { ...cur, ...patch };
    setUser(next);
    saveProfileCache(next); // persists across logout for same-device restore
    setUserState(next);

    // Attempt profile update. We fail silently to allow fallback logic in Onboarding.
    try {
      await ApiService.updateProfile(next);
    } catch (e) {
      console.error("Profile API err", e);
    }
  }, []);

  const logout = useCallback(() => {
    clearUser();
    setUserState(null);
  }, []);

  return { user, updateUser, logout };
}
