import { Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

interface Props {
  used: number;
  plan: string;
}

/** Inline card shown in chat when the monthly query quota is exhausted. */
export function RateLimitCard({ used, plan }: Props) {
  const nav = useNavigate();
  return (
    <div className="mx-auto max-w-2xl rounded-3xl border-2 border-primary/20 bg-gradient-to-br from-primary/10 to-primary/5 p-6 text-center shadow-sm">
      <div className="mx-auto mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <Rocket className="h-6 w-6" />
      </div>
      <h3 className="font-display text-xl font-black tracking-tight">
        You've used all {used} {plan === "free" ? "free" : "Plus"} questions this month! 🚀
      </h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Upgrade to keep your learning streak going.
      </p>
      <div className="mt-5 flex flex-col items-center justify-center gap-2 sm:flex-row">
        <Button
          className="rounded-pill px-6"
          onClick={() => nav("/subscribe?plan=plus")}
        >
          Upgrade to Plus ₹199/mo
        </Button>
        <Button
          variant="outline"
          className="rounded-pill px-6"
          onClick={() => nav("/subscribe?plan=pro")}
        >
          Upgrade to Pro ₹499/mo
        </Button>
      </div>
    </div>
  );
}
