import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard, Download, RefreshCw } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/hooks/useAuth";
import {
  cancelAtPeriodEnd,
  formatDate,
  formatINR,
  getInvoices,
  getPlan,
  getSubscription,
  resumeSubscription,
} from "@/lib/billing";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

const STATUS_CLS: Record<string, string> = {
  paid: "bg-success/15 text-success",
  refunded: "bg-muted text-muted-foreground",
  failed: "bg-destructive/15 text-destructive",
};

export default function SettingsSubscription() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [, force] = useState(0);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const sub = getSubscription();
  const invoices = getInvoices();
  const planDef = getPlan(user?.plan ?? "free");
  const isPaid = user?.plan && user.plan !== "free" && sub;

  const handleCancel = () => {
    cancelAtPeriodEnd();
    setConfirmOpen(false);
    force((n) => n + 1);
    toast({
      title: "Subscription will end at period end",
      description: sub ? `You'll keep access until ${formatDate(sub.renewsAt)}.` : undefined,
    });
  };

  const handleResume = () => {
    resumeSubscription();
    force((n) => n + 1);
    toast({ title: "Subscription resumed" });
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-8">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Settings
          </p>
          <h1 className="font-display text-3xl font-black sm:text-4xl">Subscription</h1>
        </header>

        {/* Current plan */}
        <section className="mb-6 rounded-3xl border border-border bg-card p-6 shadow-soft">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Current plan
              </p>
              <div className="mt-1 flex items-center gap-2">
                <h2 className="font-display text-3xl font-black">{planDef.name}</h2>
                {sub?.cancelAtPeriodEnd && (
                  <span className="rounded-pill bg-warning/15 px-2 py-0.5 text-[10px] font-bold uppercase text-warning">
                    Ending soon
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{planDef.tagline}</p>

              {isPaid && sub && (
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Billing</p>
                    <p className="font-semibold capitalize">{sub.cycle}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">
                      {sub.cancelAtPeriodEnd ? "Ends on" : "Renews on"}
                    </p>
                    <p className="font-semibold">{formatDate(sub.renewsAt)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Started</p>
                    <p className="font-semibold">{formatDate(sub.startedAt)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Last charge</p>
                    <p className="font-semibold">{formatINR(sub.amountPaid)}</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {!isPaid ? (
                <Button onClick={() => navigate("/subscribe")} className="rounded-pill">
                  Upgrade plan
                </Button>
              ) : (
                <>
                  <Button
                    variant="outline"
                    onClick={() => navigate("/subscribe")}
                    className="rounded-pill"
                  >
                    Change plan
                  </Button>
                  {sub?.cancelAtPeriodEnd ? (
                    <Button onClick={handleResume} className="rounded-pill">
                      <RefreshCw className="h-4 w-4" />
                      Resume
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={() => setConfirmOpen(true)}
                      className="rounded-pill text-destructive hover:text-destructive"
                    >
                      Cancel
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        </section>

        {/* Payment method */}
        {isPaid && (
          <section className="mb-6 rounded-3xl border border-border bg-card p-6">
            <h3 className="mb-3 font-display text-lg font-bold">Payment method</h3>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
                  <CreditCard className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold">UPI · Razorpay</p>
                  <p className="text-xs text-muted-foreground">Auto-debit on renewal</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" className="rounded-pill">
                Update
              </Button>
            </div>
          </section>
        )}

        {/* Invoices */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <h3 className="mb-4 font-display text-lg font-bold">Billing history</h3>
          {invoices.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No invoices yet. Upgrade to a paid plan to see your billing history.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="pb-2 font-semibold">Invoice</th>
                    <th className="pb-2 font-semibold">Date</th>
                    <th className="pb-2 font-semibold">Plan</th>
                    <th className="pb-2 font-semibold">Amount</th>
                    <th className="pb-2 font-semibold">Status</th>
                    <th className="pb-2 font-semibold"></th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-border last:border-0">
                      <td className="py-3 font-mono text-xs">{inv.id}</td>
                      <td className="py-3">{formatDate(inv.date)}</td>
                      <td className="py-3 capitalize">
                        {inv.plan} · {inv.cycle}
                      </td>
                      <td className="py-3 font-semibold">{formatINR(inv.amount)}</td>
                      <td className="py-3">
                        <span
                          className={cn(
                            "rounded-pill px-2 py-0.5 text-[10px] font-bold uppercase",
                            STATUS_CLS[inv.status],
                          )}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 rounded-pill"
                          onClick={() =>
                            toast({ title: "Demo", description: "PDF download coming soon." })
                          }
                        >
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent className="rounded-3xl">
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel subscription?</AlertDialogTitle>
            <AlertDialogDescription>
              You'll keep access to {planDef.name} until{" "}
              {sub ? formatDate(sub.renewsAt) : "the end of your billing period"}, then drop to Free.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-pill">Keep plan</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancel}
              className="rounded-pill bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Cancel anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
