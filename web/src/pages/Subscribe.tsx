import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { CycleToggle } from "@/components/subscribe/CycleToggle";
import { PlanCard } from "@/components/subscribe/PlanCard";
import { RazorpayMockDialog } from "@/components/subscribe/RazorpayMockDialog";
import { useAuth } from "@/hooks/useAuth";
import { clearPendingPlan, getPendingPlan, type Plan } from "@/lib/auth";
import { PLANS, type BillingCycle } from "@/lib/billing";
import { toast } from "@/hooks/use-toast";

const FAQS = [
  {
    q: "Can I cancel anytime?",
    a: "Yes. You keep access until the end of your billing period, then drop to Free. No questions asked.",
  },
  {
    q: "What happens to my unused questions?",
    a: "Question quotas reset every month and don't roll over — but Pro is unlimited so you'll never run out.",
  },
  {
    q: "Do you offer student discounts?",
    a: "Annual billing already saves you ~20%. Refer 5 friends in a month and you get a free Plus month.",
  },
  {
    q: "How fast are teacher tickets answered?",
    a: "Pro tickets are typically answered within a few minutes by qualified teachers, depending on subject.",
  },
];

export default function Subscribe() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [cycle, setCycle] = useState<BillingCycle>("annual");
  const [pickedPlan, setPickedPlan] = useState<Plan | null>(null);
  const [open, setOpen] = useState(false);

  // Auto-open checkout when arriving with ?plan=plus|pro
  const initialPlan = useMemo<Plan | null>(() => {
    const fromUrl = params.get("plan");
    if (fromUrl === "plus" || fromUrl === "pro") return fromUrl;
    const pending = getPendingPlan();
    return pending;
  }, [params]);

  useEffect(() => {
    if (initialPlan && user?.plan !== initialPlan) {
      setPickedPlan(initialPlan);
      setOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = (plan: Plan) => {
    if (plan === "free") {
      navigate("/chat");
      return;
    }
    setPickedPlan(plan);
    setOpen(true);
  };

  const handleSuccess = (plan: Plan) => {
    setOpen(false);
    clearPendingPlan();
    updateUser({ plan });
    toast({
      title: "Subscription active 🎉",
      description: `You're now on Javaab ${plan === "plus" ? "Plus" : "Pro"}.`,
    });
    navigate("/settings/subscription");
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-16">
        {/* Hero */}
        <div className="mb-10 text-center">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-pill bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Pricing
          </div>
          <h1 className="font-display text-4xl font-black leading-[1.05] sm:text-5xl">
            Less doubt.
            <br className="sm:hidden" /> More marks.
          </h1>
          <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
            Pick a plan that fits how you study. Cancel anytime — no fine print.
          </p>

          <div className="mt-6 flex justify-center">
            <CycleToggle cycle={cycle} onChange={setCycle} />
          </div>
        </div>

        {/* Plans */}
        <div className="grid gap-5 md:grid-cols-3">
          {PLANS.map((p) => (
            <PlanCard
              key={p.id}
              def={p}
              cycle={cycle}
              currentPlan={user?.plan ?? "free"}
              onSelect={handleSelect}
            />
          ))}
        </div>

        {/* Trust strip */}
        <div className="mt-10 grid gap-4 rounded-3xl border border-border bg-card p-6 sm:grid-cols-3">
          {[
            {
              t: "Cancel anytime",
              d: "Stop whenever, keep access till period end.",
            },
            {
              t: "UPI & cards",
              d: "Pay via any UPI app or card — secured by Razorpay.",
            },
            {
              t: "7-day refund",
              d: "Not loving it? Email us within 7 days for a full refund.",
            },
          ].map((x) => (
            <div key={x.t}>
              <p className="font-display text-lg font-bold">{x.t}</p>
              <p className="text-sm text-muted-foreground">{x.d}</p>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <section className="mt-12">
          <h2 className="mb-5 font-display text-2xl font-black">
            Quick answers
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {FAQS.map((f) => (
              <div
                key={f.q}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <p className="font-display font-bold">{f.q}</p>
                <p className="mt-1.5 text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <RazorpayMockDialog
        open={open}
        plan={pickedPlan}
        cycle={cycle}
        onClose={() => setOpen(false)}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
