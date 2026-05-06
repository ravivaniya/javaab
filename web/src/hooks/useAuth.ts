import { useCallback, useEffect, useState } from "react";
import {
  Board,
  clearUser,
  DifficultSubject,
  getSavedProfile,
  getUser,
  InputMode,
  JavaabUser,
  Lang,
  mockSendOtp,
  mockVerifyOtp,
  Plan,
  saveProfileCache,
  setToken,
  setUser,
  StudyMethod,
  StudyStruggle,
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

    // Decode JWT payload (no signature check — just extracting claims for UX).
    let jwtRole: string | undefined;
    try {
      const parts = verify.access_token.split(".");
      if (parts.length === 3) {
        const decoded = JSON.parse(atob(parts[1]));
        jwtRole = decoded.role;
      }
    } catch { /* non-fatal */ }

    // OTP confirmed — now build/refresh the local user record.
    const u = await mockVerifyOtp(phone, code);
    const validRole = (["student", "teacher", "admin"] as const).find(r => r === jwtRole);
    if (validRole) u.role = validRole;

    // Restore profile from local cache immediately (works even without Cosmos DB).
    const cached = getSavedProfile(phone);
    if (cached) Object.assign(u, cached);

    setUser(u);
    setUserState(u);

    // Mirror the user into the backend so /auth/profile etc. work.
    try {
      await ApiService.registerUser({ phone });
    } catch (e) {
      console.error("Register API err", e);
    }

    // Restore full profile from backend (persists across logout/login).
    try {
      const profileRes = await ApiService.getProfile();
      if (profileRes?.user) {
        const b = profileRes.user as Partial<JavaabUser> & Record<string, unknown>;
        const tier = String(b.plan ?? b.tier ?? "free").toLowerCase();
        const merged: JavaabUser = {
          ...u,
          ...(b.name !== undefined && { name: b.name as string }),
          ...(b.board !== undefined && { board: b.board as Board }),
          ...(b.classNum !== undefined && { classNum: b.classNum as number }),
          ...(b.languages !== undefined && { languages: b.languages as Lang[] }),
          ...(b.plan !== undefined && { plan: (tier === "plus" || tier === "pro" ? tier : "free") as Plan }),
          ...(b.attendsCoaching !== undefined && { attendsCoaching: b.attendsCoaching as boolean }),
          ...(b.difficultSubjects !== undefined && { difficultSubjects: b.difficultSubjects as DifficultSubject[] }),
          ...(b.studyMethod !== undefined && { studyMethod: b.studyMethod as StudyMethod }),
          ...(b.studyStruggle !== undefined && { studyStruggle: b.studyStruggle as StudyStruggle }),
          ...(b.preferredInputMode !== undefined && { preferredInputMode: b.preferredInputMode as InputMode }),
          ...(b.isOnboarded !== undefined && { isOnboarded: b.isOnboarded as boolean }),
        };
        setUser(merged);
        setUserState(merged);
        return merged;
      }
    } catch (e) {
      console.error("Profile fetch err", e);
    }
    return u;
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

  return { user, sendOtp, verifyOtp, updateUser, logout };
}
