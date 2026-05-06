/**
 * Mock auth store backed by localStorage.
 * Phase 1: no backend. Replace with Lovable Cloud later.
 */

export type Plan = "free" | "plus" | "pro";
export type Board = "cbse" | "gseb";
export type Lang = "en" | "hi" | "gu";
export type StudyMethod = "textbook" | "notes" | "videos" | "coaching";
export type StudyStruggle =
  | "forget_later"
  | "dont_understand"
  | "cant_solve"
  | "cant_write"
  | "run_out_of_time";
export type InputMode = "type" | "photo" | "voice";
export type DifficultSubject = "maths" | "science" | "social" | "english" | "hindi" | "gujarati";

export interface JavaabUser {
  phone: string;            // 10-digit, no prefix
  name?: string;            // optional display name (max 20 chars)
  role?: "student" | "teacher" | "admin";
  isOnboarded: boolean;
  board?: Board;
  classNum?: number;        // 6..12
  languages?: Lang[];
  attendsCoaching?: boolean;
  difficultSubjects?: DifficultSubject[];
  studyMethod?: StudyMethod;
  studyStruggle?: StudyStruggle;
  preferredInputMode?: InputMode;
  plan: Plan;
  createdAt: number;
}

const USER_KEY = "javaab.user";
const PENDING_PLAN_KEY = "javaab.pendingPlan";
const KNOWN_PHONES_KEY = "javaab.knownPhones";
const TOKEN_KEY = "javaab.token";
const profileCacheKey = (phone: string) => `javaab.profile.${phone}`;

/** Read the stored JWT (or null). */
export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Persist or clear the JWT. */
export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* noop */
  }
}

export function clearToken(): void {
  setToken(null);
}

/** Read current authenticated user (or null). */
export function getUser(): JavaabUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as JavaabUser) : null;
  } catch {
    return null;
  }
}

/** Persist user. */
export function setUser(user: JavaabUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event("javaab:auth"));
}

/**
 * Save a full profile snapshot keyed by phone.
 * Survives logout — allows profile restoration on re-login without Cosmos DB.
 */
export function saveProfileCache(user: JavaabUser): void {
  try {
    localStorage.setItem(profileCacheKey(user.phone), JSON.stringify(user));
  } catch { /* noop */ }
}

/** Retrieve the cached profile for a phone (or null if none). */
export function getSavedProfile(phone: string): Partial<JavaabUser> | null {
  try {
    const raw = localStorage.getItem(profileCacheKey(phone));
    return raw ? (JSON.parse(raw) as Partial<JavaabUser>) : null;
  } catch {
    return null;
  }
}

/** Clear session. */
export function clearUser(): void {
  localStorage.removeItem(USER_KEY);
  clearToken();
  window.dispatchEvent(new Event("javaab:auth"));
}

/** Has this phone signed in before? Used to decide onboarding redirect. */
export function isReturningPhone(phone: string): boolean {
  try {
    const raw = localStorage.getItem(KNOWN_PHONES_KEY);
    const arr: string[] = raw ? JSON.parse(raw) : [];
    return arr.includes(phone);
  } catch {
    return false;
  }
}

/** Mark phone as known (called on first successful verify). */
export function rememberPhone(phone: string): void {
  try {
    const raw = localStorage.getItem(KNOWN_PHONES_KEY);
    const arr: string[] = raw ? JSON.parse(raw) : [];
    if (!arr.includes(phone)) arr.push(phone);
    localStorage.setItem(KNOWN_PHONES_KEY, JSON.stringify(arr));
  } catch {
    /* noop */
  }
}

/** Pending upgrade plan (from ?plan= query param). */
export function setPendingPlan(plan: Plan | null): void {
  if (plan && plan !== "free") sessionStorage.setItem(PENDING_PLAN_KEY, plan);
  else sessionStorage.removeItem(PENDING_PLAN_KEY);
}

export function getPendingPlan(): Plan | null {
  const v = sessionStorage.getItem(PENDING_PLAN_KEY);
  return v === "plus" || v === "pro" ? v : null;
}

export function clearPendingPlan(): void {
  sessionStorage.removeItem(PENDING_PLAN_KEY);
}

/**
 * Mocked send-OTP. In real world, calls backend → SMS.
 * Returns immediately. The OTP for the prototype is always 123456.
 */
export async function mockSendOtp(_phone: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 600));
}

/** Mocked verify. Accepts any 6-digit code; "123456" is the canonical demo OTP. */
export async function mockVerifyOtp(phone: string, code: string): Promise<JavaabUser> {
  await new Promise((r) => setTimeout(r, 500));
  if (!/^\d{6}$/.test(code)) throw new Error("Enter the 6-digit OTP.");

  const returning = isReturningPhone(phone);
  rememberPhone(phone);

  if (returning) {
    // Return existing user record if any, else hydrate a basic one.
    const existing = getUser();
    if (existing && existing.phone === phone) return existing;
    const user: JavaabUser = {
      phone,
      isOnboarded: true,
      board: "cbse",
      classNum: 10,
      languages: ["en"],
      plan: "free",
      createdAt: Date.now(),
    };
    setUser(user);
    return user;
  }

  const fresh: JavaabUser = {
    phone,
    isOnboarded: false,
    plan: "free",
    createdAt: Date.now(),
  };
  setUser(fresh);
  return fresh;
}
