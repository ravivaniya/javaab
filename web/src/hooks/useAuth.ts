import { useCallback, useEffect, useState } from "react";
import {
  clearUser,
  getUser,
  JavaabUser,
  mockSendOtp,
  mockVerifyOtp,
  setToken,
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

  const sendOtp = useCallback(async (phone: string) => {
    await mockSendOtp(phone);
    // Best-effort backend OTP request (mock backend just confirms).
    try {
      await ApiService.loginRequestOtp(phone);
    } catch (e) {
      console.error("Login OTP API err", e);
    }
  }, []);

  const verifyOtp = useCallback(async (phone: string, code: string) => {
    if (!/^\d{6}$/.test(code)) throw new Error("Enter the 6-digit OTP.");

    // Backend is authoritative for OTP validity — must succeed before we
    // persist any local session, otherwise wrong OTPs would log the user in.
    const verify = await ApiService.verifyOtpRemote(phone, code);
    if (!verify?.access_token) throw new Error("Invalid OTP");
    setToken(verify.access_token);

    // OTP confirmed — now build/refresh the local user record.
    const u = await mockVerifyOtp(phone, code);
    setUserState(u);

    // Mirror the user into the backend so /auth/profile etc. work.
    try {
      await ApiService.registerUser({ phone });
    } catch (e) {
      console.error("Register API err", e);
    }
    return u;
  }, []);

  const updateUser = useCallback(async (patch: Partial<JavaabUser>) => {
    const cur = getUser();
    if (!cur) return;
    const next = { ...cur, ...patch };
    setUser(next);
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

  return { user, sendOtp, verifyOtp, updateUser, logout };
}
