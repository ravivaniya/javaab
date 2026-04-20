import { cn } from "@/lib/utils";
import type { BillingCycle } from "@/lib/billing";

interface Props {
  cycle: BillingCycle;
  onChange: (c: BillingCycle) => void;
}

export function CycleToggle({ cycle, onChange }: Props) {
  return (
    <div className="inline-flex items-center rounded-pill border border-border bg-card p-1 shadow-soft">
      {(["monthly", "annual"] as BillingCycle[]).map((c) => {
        const active = cycle === c;
        return (
          <button
            key={c}
            type="button"
            onClick={() => onChange(c)}
            className={cn(
              "relative rounded-pill px-5 py-2 text-sm font-semibold transition-all",
              active
                ? "bg-foreground text-background shadow"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {c === "monthly" ? "Monthly" : "Annual"}
            {c === "annual" && (
              <span className="ml-1.5 rounded-pill bg-success/20 px-1.5 py-0.5 text-[10px] font-bold text-success">
                -20%
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
