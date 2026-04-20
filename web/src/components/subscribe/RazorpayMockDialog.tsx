import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Lock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { formatINR, mockCharge, priceFor, getPlan, type BillingCycle } from "@/lib/billing";
import type { Plan } from "@/lib/auth";

interface Props {
  open: boolean;
  plan: Plan | null;
  cycle: BillingCycle;
  onClose: () => void;
  onSuccess: (plan: Plan) => void;
}

type Stage = "review" | "processing" | "success";

export function RazorpayMockDialog({ open, plan, cycle, onClose, onSuccess }: Props) {
  const [stage, setStage] = useState<Stage>("review");

  useEffect(() => {
    if (open) setStage("review");
  }, [open, plan]);

  if (!plan) return null;
  const def = getPlan(plan);
  const amount = priceFor(def, cycle);

  const handlePay = async () => {
    setStage("processing");
    await mockCharge(plan, cycle);
    setStage("success");
    setTimeout(() => onSuccess(plan), 1400);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && stage !== "processing" && onClose()}>
      <DialogContent className="rounded-3xl sm:max-w-md">
        {stage === "review" && (
          <>
            <DialogHeader>
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                <Lock className="h-3.5 w-3.5" />
                Secure checkout · Razorpay
              </div>
              <DialogTitle className="font-display text-2xl font-black">
                Pay {formatINR(amount)}
              </DialogTitle>
              <DialogDescription>
                {def.name} · {cycle === "monthly" ? "Monthly" : "Annual"} subscription
              </DialogDescription>
            </DialogHeader>

            <div className="my-2 space-y-3 rounded-2xl border border-border bg-muted/30 p-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Plan</span>
                <span className="font-semibold">{def.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Billing</span>
                <span className="font-semibold capitalize">{cycle}</span>
              </div>
              <div className="flex justify-between border-t border-border pt-3">
                <span className="font-semibold">Total</span>
                <span className="font-display text-lg font-black">{formatINR(amount)}</span>
              </div>
            </div>

            <p className="text-[11px] text-muted-foreground">
              This is a demo flow. No real payment is processed.
            </p>

            <Button
              onClick={handlePay}
              className="h-12 rounded-pill text-base font-bold"
            >
              Pay {formatINR(amount)} via UPI
            </Button>
          </>
        )}

        {stage === "processing" && (
          <div className="flex flex-col items-center gap-4 py-10">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="font-display text-lg font-bold">Processing payment…</p>
            <p className="text-sm text-muted-foreground">Talking to your bank</p>
          </div>
        )}

        {stage === "success" && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <div className="grid h-16 w-16 place-items-center rounded-full bg-success/15">
              <CheckCircle2 className="h-9 w-9 text-success" />
            </div>
            <h3 className="font-display text-2xl font-black">Welcome to {def.name}!</h3>
            <p className="text-sm text-muted-foreground">
              Payment of {formatINR(amount)} successful.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
