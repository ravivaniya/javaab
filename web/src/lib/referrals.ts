/**
 * Mock referral system backed by localStorage.
 */

export type ReferralStatus = "signed_up" | "completed_5" | "rewarded";

export interface Referral {
  id: string;
  name: string;          // raw name; mask before display
  joinedAt: number;
  status: ReferralStatus;
}

export interface LeaderRow {
  rank: number;
  name: string;          // already masked
  count: number;
  badge?: "👑" | "🔥" | "⭐";
}

const CODE_KEY = "javaab.refCode";
const REFS_KEY = "javaab.referrals";
const SEED_KEY = "javaab.refSeeded";

const SAMPLE = [
  ["Rohan Sharma", 14, "signed_up"],
  ["Priya Patel", 9, "rewarded"],
  ["Aman Verma", 5, "completed_5"],
  ["Sneha Iyer", 21, "rewarded"],
  ["Karan Mehta", 2, "signed_up"],
  ["Anjali Joshi", 28, "rewarded"],
] as const;

export function getCode(phone?: string): string {
  let code = localStorage.getItem(CODE_KEY);
  if (code) return code;
  const tail = (phone ?? "").slice(-4) || Math.floor(1000 + Math.random() * 9000).toString();
  code = "JV" + tail;
  localStorage.setItem(CODE_KEY, code);
  return code;
}

export function getReferralUrl(code: string): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "https://app.tryjavaab.com";
  return `${origin}/login?ref=${code}`;
}

export function getReferrals(): Referral[] {
  try {
    if (!localStorage.getItem(SEED_KEY)) {
      const now = Date.now();
      const seeded: Referral[] = SAMPLE.map(([name, daysAgo, status], i) => ({
        id: "R" + (i + 1),
        name: name as string,
        joinedAt: now - (daysAgo as number) * 24 * 3600 * 1000,
        status: status as ReferralStatus,
      }));
      localStorage.setItem(REFS_KEY, JSON.stringify(seeded));
      localStorage.setItem(SEED_KEY, "1");
    }
    const raw = localStorage.getItem(REFS_KEY);
    return raw ? (JSON.parse(raw) as Referral[]) : [];
  } catch {
    return [];
  }
}

/** Mask a name like "Rohan Sharma" → "R***n S***a". */
export function maskName(name: string): string {
  return name
    .split(" ")
    .map((part) => {
      if (part.length <= 2) return part[0] + "*";
      return part[0] + "***" + part[part.length - 1];
    })
    .join(" ");
}

export function statusLabel(s: ReferralStatus): string {
  switch (s) {
    case "signed_up": return "Signed up";
    case "completed_5": return "Completed 5 queries";
    case "rewarded": return "Reward granted";
  }
}

export interface ReferralStats {
  referred: number;
  joined: number;
  bonusQuestions: number;
  thisMonth: number;
}

export function getStats(): ReferralStats {
  const refs = getReferrals();
  const now = new Date();
  const thisMonth = refs.filter((r) => {
    const d = new Date(r.joinedAt);
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }).length;
  const completed = refs.filter((r) => r.status !== "signed_up").length;
  return {
    referred: refs.length,
    joined: refs.length,
    bonusQuestions: completed * 50,
    thisMonth,
  };
}

export function getLeaderboard(): LeaderRow[] {
  return [
    { rank: 1, name: "A***a J***i", count: 42, badge: "👑" },
    { rank: 2, name: "S***a I***r", count: 31, badge: "🔥" },
    { rank: 3, name: "P***a P***l", count: 27, badge: "⭐" },
    { rank: 4, name: "R***n S***a", count: 19 },
    { rank: 5, name: "A***n V***a", count: 14 },
  ];
}
