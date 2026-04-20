import { useCallback, useEffect, useState } from "react";
import {
  clearUser,
  getUser,
  JavaabUser,
  mockSendOtp,
  mockVerifyOtp,
  setUser,
} from "@/lib/auth";

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

  const sendOtp = useCallback(async (phone: string) => {
    await mockSendOtp(phone);
  }, []);

  const verifyOtp = useCallback(async (phone: string, code: string) => {
    const u = await mockVerifyOtp(phone, code);
    setUserState(u);
    return u;
  }, []);

  const updateUser = useCallback((patch: Partial<JavaabUser>) => {
    const cur = getUser();
    if (!cur) return;
    const next = { ...cur, ...patch };
    setUser(next);
    setUserState(next);
  }, []);

  const logout = useCallback(() => {
    clearUser();
    setUserState(null);
  }, []);

  return { user, sendOtp, verifyOtp, updateUser, logout };
}
