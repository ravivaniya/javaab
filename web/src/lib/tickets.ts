/**
 * Mocked teacher-ticket store. Pro-only feature.
 * 3 tickets/month per Pro user.
 */

export type TicketStatus = "open" | "with_teacher" | "answered";

export interface Ticket {
  id: string;                       // TKT-MMDD-XXX
  question: string;
  subject?: string;                 
  imageUrl?: string;
  aiAttempt?: string;
  status: TicketStatus;
  createdAt: number;
  assignedTeacher?: string;
  teacherCredentials?: string;
  answer?: string;
  answeredAt?: number;
  savedToCache?: boolean;
}

const KEY = "javaab.tickets";
const QUOTA_PER_MONTH = 3;

function bucket(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function storeKey(phone: string) {
  return `${KEY}.${phone}`;
}

export function loadTickets(phone: string): Ticket[] {
  try {
    const raw = localStorage.getItem(storeKey(phone));
    const arr: Ticket[] = raw ? JSON.parse(raw) : [];
    return arr.sort((a, b) => b.createdAt - a.createdAt);
  } catch {
    return [];
  }
}

function persist(phone: string, list: Ticket[]) {
  localStorage.setItem(storeKey(phone), JSON.stringify(list));
  window.dispatchEvent(new Event("javaab:tickets"));
}

export function getMonthlyUsage(phone: string): number {
  const b = bucket();
  return loadTickets(phone).filter((t) => {
    const d = new Date(t.createdAt);
    const tb = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    return tb === b;
  }).length;
}

export function getTicketQuota() {
  return QUOTA_PER_MONTH;
}

export function nextResetDate(): string {
  const d = new Date();
  const next = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  return next.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function genId(): string {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const seq = String(Math.floor(Math.random() * 900) + 100);
  return `TKT-${mm}${dd}-${seq}`;
}

const TEACHERS = [
  { name: "Mrs. Patel", credentials: "Chemistry — 11 yrs exp" },
  { name: "Mr. Kulkarni", credentials: "Mathematics — 14 yrs exp" },
  { name: "Ms. Iyer", credentials: "English — 9 yrs exp" },
  { name: "Dr. Sharma", credentials: "Physics — 17 yrs exp" },
];

/** Create a ticket — simulates queueing. After ~6s flips to "with_teacher". */
export function createTicket(
  phone: string,
  input: { question: string; aiAttempt?: string; imageUrl?: string },
): Ticket {
  const list = loadTickets(phone);
  const t: Ticket = {
    id: genId(),
    question: input.question,
    aiAttempt: input.aiAttempt,
    imageUrl: input.imageUrl,
    status: "open",
    createdAt: Date.now(),
  };
  list.unshift(t);
  persist(phone, list);

  // Mock progression: open → with_teacher (6s) → answered (12s)
  const teacher = TEACHERS[Math.floor(Math.random() * TEACHERS.length)];
  setTimeout(() => updateTicket(phone, t.id, { status: "with_teacher", assignedTeacher: teacher.name, teacherCredentials: teacher.credentials }), 6000);
  setTimeout(() => updateTicket(phone, t.id, {
    status: "answered",
    answer: mockTeacherAnswer(input.question),
    answeredAt: Date.now(),
    savedToCache: Math.random() > 0.3,
  }), 12000);

  return t;
}

export function updateTicket(phone: string, id: string, patch: Partial<Ticket>) {
  const list = loadTickets(phone);
  const idx = list.findIndex((t) => t.id === id);
  if (idx === -1) return;
  list[idx] = { ...list[idx], ...patch };
  persist(phone, list);
}

export function getTicket(phone: string, id: string): Ticket | undefined {
  return loadTickets(phone).find((t) => t.id === id);
}

function mockTeacherAnswer(q: string): string {
  return `Great question! Here's the proper approach:

**Step 1.** Identify what's being asked.

**Step 2.** Apply the formula carefully. For problems like *"${q.slice(0, 60)}..."* the standard method is:

$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$

**Step 3.** Substitute values, simplify, and verify the answer makes physical sense.

**Common mistake students make:** forgetting to check the discriminant (b² − 4ac) before solving — if it's negative, there are no real roots.

I hope this clears it up! Practice 2–3 similar problems from your NCERT exercise to lock the concept in.`;
}

/** Format relative time like "2 days ago". */
export function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
