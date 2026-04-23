/**
 * Mock billing/subscription store backed by localStorage.
 * Replace with Razorpay + Lovable Cloud later.
 */
import type { Plan } from "@/lib/auth";

export type BillingCycle = "monthly" | "annual";
export type InvoiceStatus = "paid" | "refunded" | "failed";

export interface PlanDef {
  id: Plan;
  name: string;
  tagline: string;
  monthly: number;        // INR
  annual: number;         // INR (per year, already discounted)
  highlight?: boolean;
  features: string[];
  notIncluded?: string[];
}

export interface Subscription {
  plan: Plan;
  cycle: BillingCycle;
  startedAt: number;
  renewsAt: number;       // ms
  cancelAtPeriodEnd: boolean;
  amountPaid: number;     // INR last charge
}

export interface Invoice {
  id: string;
  date: number;
  plan: Plan;
  cycle: BillingCycle;
  amount: number;
  status: InvoiceStatus;
  method: string;         // "UPI · Razorpay" etc
}

const SUB_KEY = "javaab.subscription";
const INV_KEY = "javaab.invoices";

export const PLANS: PlanDef[] = [
  {
    id: "free",
    name: "Free",
    tagline: "Explore & learn",
    monthly: 0,
    annual: 0,
    features: [
      "50 questions per month",
      "Text input only",
      "CBSE & GSEB Syllabus",
      "7-day history",
    ],
    notIncluded: ["Photo / Image input", "Teacher tickets"],
  },
  {
    id: "plus",
    name: "Plus",
    tagline: "For curious students",
    monthly: 199,
    annual: 1990,
    highlight: true,
    features: [
      "1,000 questions per month",
      "Photo / Image input",
      "90-day history",
      "Basic exam tips",
    ],
    notIncluded: ["Teacher tickets"],
  },
  {
    id: "pro",
    name: "Pro",
    tagline: "For serious learners",
    monthly: 499,
    annual: 4990,
    features: [
      "Unlimited questions",
      "Dedicated priority queue",
      "Teacher Tickets (3/mo)",
      "Full PYQ analysis",
      "Unlimited history",
    ],
  },
];

export function getPlan(id: Plan): PlanDef {
  return PLANS.find((p) => p.id === id)!;
}

export function priceFor(plan: PlanDef, cycle: BillingCycle): number {
  return cycle === "monthly" ? plan.monthly : plan.annual;
}

export function annualSavingsPct(plan: PlanDef): number {
  if (!plan.monthly) return 0;
  const fullYear = plan.monthly * 12;
  return Math.round(((fullYear - plan.annual) / fullYear) * 100);
}

/* ------------ Subscription store ------------ */

export function getSubscription(): Subscription | null {
  try {
    const raw = localStorage.getItem(SUB_KEY);
    return raw ? (JSON.parse(raw) as Subscription) : null;
  } catch {
    return null;
  }
}

export function setSubscription(sub: Subscription | null): void {
  if (sub) localStorage.setItem(SUB_KEY, JSON.stringify(sub));
  else localStorage.removeItem(SUB_KEY);
  window.dispatchEvent(new Event("javaab:billing"));
}

export function getInvoices(): Invoice[] {
  try {
    const raw = localStorage.getItem(INV_KEY);
    return raw ? (JSON.parse(raw) as Invoice[]) : [];
  } catch {
    return [];
  }
}

function addInvoice(inv: Invoice): void {
  const all = getInvoices();
  all.unshift(inv);
  localStorage.setItem(INV_KEY, JSON.stringify(all));
}

/** Mock the Razorpay charge → returns invoice. */
export async function mockCharge(plan: Plan, cycle: BillingCycle): Promise<Invoice> {
  const def = getPlan(plan);
  const amount = priceFor(def, cycle);
  await new Promise((r) => setTimeout(r, 1400));

  const now = Date.now();
  const periodMs = cycle === "monthly" ? 30 * 24 * 3600 * 1000 : 365 * 24 * 3600 * 1000;
  const sub: Subscription = {
    plan,
    cycle,
    startedAt: now,
    renewsAt: now + periodMs,
    cancelAtPeriodEnd: false,
    amountPaid: amount,
  };
  setSubscription(sub);

  const inv: Invoice = {
    id: "INV-" + now.toString(36).toUpperCase(),
    date: now,
    plan,
    cycle,
    amount,
    status: "paid",
    method: "UPI · Razorpay",
  };
  addInvoice(inv);
  return inv;
}

export function cancelAtPeriodEnd(): void {
  const sub = getSubscription();
  if (!sub) return;
  setSubscription({ ...sub, cancelAtPeriodEnd: true });
}

export function resumeSubscription(): void {
  const sub = getSubscription();
  if (!sub) return;
  setSubscription({ ...sub, cancelAtPeriodEnd: false });
}

export function formatINR(n: number): string {
  return "₹" + n.toLocaleString("en-IN");
}

export function formatDate(ms: number): string {
  return new Date(ms).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
