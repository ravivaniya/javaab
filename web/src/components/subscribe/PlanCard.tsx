import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  annualSavingsPct,
  formatINR,
  priceFor,
  type BillingCycle,
  type PlanDef,
} from "@/lib/billing";
import type { Plan } from "@/lib/auth";

interface Props {
  def: PlanDef;
  cycle: BillingCycle;
  currentPlan: Plan;
  onSelect: (plan: Plan) => void;
  loading?: boolean;
}

const ACCENT: Record<Plan, string> = {
  free: "border-border",
  plus: "border-[hsl(var(--plus))]/40 ring-1 ring-[hsl(var(--plus))]/20",
  pro: "border-[hsl(var(--pro))]/40",
};

export function PlanCard({ def, cycle, currentPlan, onSelect, loading }: Props) {
  const price = priceFor(def, cycle);
  const isCurrent = currentPlan === def.id;
  const isFree = def.id === "free";
  const monthlyEquiv = cycle === "annual" && !isFree ? Math.round(def.annual / 12) : null;
  const savings = cycle === "annual" ? annualSavingsPct(def) : 0;

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-3xl border bg-card p-6 shadow-soft transition-all",
        ACCENT[def.id],
        def.highlight && "scale-[1.02] shadow-glow",
      )}
    >
      {def.highlight && (
        <span className="absolute -top-3 left-6 rounded-pill bg-[hsl(var(--plus))] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white">
          Most popular
        </span>
      )}

      <div className="mb-4">
        <h3 className="font-display text-2xl font-black">{def.name}</h3>
        <p className="text-sm text-muted-foreground">{def.tagline}</p>
      </div>

      <div className="mb-5">
        {isFree ? (
          <div className="font-display text-4xl font-black">₹0</div>
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="font-display text-4xl font-black">{formatINR(price)}</span>
            <span className="text-sm text-muted-foreground">
              /{cycle === "monthly" ? "mo" : "yr"}
            </span>
          </div>
        )}
        {monthlyEquiv !== null && (
          <p className="mt-1 text-xs text-muted-foreground">
            ≈ {formatINR(monthlyEquiv)}/mo
            {savings > 0 && (
              <span className="ml-1.5 rounded-pill bg-success/15 px-1.5 py-0.5 text-[10px] font-bold text-success">
                Save {savings}%
              </span>
            )}
          </p>
        )}
      </div>

      <ul className="mb-6 space-y-2.5 text-sm">
        {def.features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            <span>{f}</span>
          </li>
        ))}
        {def.notIncluded?.map((f) => (
          <li key={f} className="flex items-start gap-2 text-muted-foreground">
            <X className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="line-through decoration-1">{f}</span>
          </li>
        ))}
      </ul>

      <Button
        onClick={() => onSelect(def.id)}
        disabled={isCurrent || loading}
        className={cn(
          "mt-auto h-11 rounded-pill text-sm font-bold",
          def.id === "plus" && !isCurrent && "bg-[hsl(var(--plus))] text-white hover:bg-[hsl(var(--plus))]/90",
          def.id === "pro" && !isCurrent && "bg-[hsl(var(--pro))] text-white hover:bg-[hsl(var(--pro))]/90",
        )}
        variant={isFree && !isCurrent ? "outline" : "default"}
      >
        {isCurrent ? "Current plan" : isFree ? "Stay on Free" : `Get ${def.name}`}
      </Button>
    </div>
  );
}
