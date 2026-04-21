import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Plus, Sparkles } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/tickets/StatusBadge";
import { RaiseTicketDialog } from "@/components/tickets/RaiseTicketDialog";
import { useAuth } from "@/hooks/useAuth";
import {
  getMonthlyUsage,
  getTicketQuota,
  loadTickets,
  nextResetDate,
  relativeTime,
  type Ticket,
} from "@/lib/tickets";

export default function Tickets() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [openDialog, setOpenDialog] = useState(false);

  // Reactive load
  useEffect(() => {
    if (!user) return;
    const sync = () => setTickets(loadTickets(user.phone));
    sync();
    window.addEventListener("javaab:tickets", sync);
    const poll = setInterval(sync, 2000); // pick up mock status flips
    return () => {
      window.removeEventListener("javaab:tickets", sync);
      clearInterval(poll);
    };
  }, [user]);

  const isPro = user?.plan === "pro";
  const quota = getTicketQuota();
  const used = user ? getMonthlyUsage(user.phone) : 0;
  const remaining = Math.max(0, quota - used);

  if (!isPro) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 text-center sm:py-24">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-pro/10 text-pro">
            <Lock className="h-9 w-9" />
          </div>
          <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">
            Teacher Tickets are a Pro feature
          </h1>
          <p className="mt-3 max-w-md text-muted-foreground">
            Stuck on something AI can't crack? Upgrade to Pro and get answers from real,
            verified teachers — within 24 hours.
          </p>

          <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              { t: "3 tickets / month", s: "Personally answered" },
              { t: "Verified teachers", s: "Subject experts only" },
              { t: "Saved to your account", s: "Re-read anytime" },
            ].map((b) => (
              <div
                key={b.t}
                className="rounded-2xl bg-card p-4 text-left ring-1 ring-border"
              >
                <p className="text-sm font-bold">{b.t}</p>
                <p className="text-xs text-muted-foreground">{b.s}</p>
              </div>
            ))}
          </div>

          <Button
            onClick={() => nav("/subscribe?plan=pro")}
            className="mt-8 rounded-pill bg-pro px-8 py-6 text-base font-bold hover:bg-pro/90"
          >
            <Sparkles className="h-4 w-4" />
            Upgrade to Pro
          </Button>
        </main>
      </div>
    );
  }

  const usagePct = (used / quota) * 100;
  const atLimit = remaining === 0;

  return (
    <TooltipProvider delayDuration={150}>
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-10">
          {/* Header */}
          <div className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">
                🎓 Teacher Tickets
              </h1>
              <p className="mt-2 text-muted-foreground">
                Real answers from verified teachers, saved to your account.
              </p>
            </div>

            <div className="flex flex-col items-stretch gap-3 sm:items-end">
              <div className="w-full min-w-[220px] rounded-2xl bg-card p-3 ring-1 ring-border sm:w-auto">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span>{used} of {quota} used this month</span>
                  <span className="text-muted-foreground">Resets {nextResetDate()}</span>
                </div>
                <Progress value={usagePct} className="mt-2 h-1.5" />
              </div>

              {atLimit ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span tabIndex={0}>
                      <Button disabled className="rounded-pill">
                        <Plus className="h-4 w-4" />
                        Raise New Ticket
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>Resets on {nextResetDate()}</TooltipContent>
                </Tooltip>
              ) : (
                <Button onClick={() => setOpenDialog(true)} className="rounded-pill">
                  <Plus className="h-4 w-4" />
                  Raise New Ticket
                </Button>
              )}
            </div>
          </div>

          {/* List */}
          {tickets.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-border bg-card/60 p-10 text-center">
              <p className="font-display text-2xl font-black">No tickets yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Raise your first one when AI can't quite get there.
              </p>
              <Button
                onClick={() => setOpenDialog(true)}
                className="mt-5 rounded-pill"
              >
                <Plus className="h-4 w-4" />
                Raise a ticket
              </Button>
            </div>
          ) : (
            <ul className="space-y-3">
              {tickets.map((t) => (
                <li key={t.id}>
                  <Link
                    to={`/tickets/${t.id}`}
                    className="group block rounded-3xl bg-card p-5 ring-1 ring-border transition-all hover:shadow-soft hover:ring-primary/30"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span className="font-mono font-semibold tracking-wide">{t.id}</span>
                      <StatusBadge status={t.status} />
                    </div>
                    <p className="mt-2 line-clamp-2 text-base font-semibold leading-snug">
                      {t.question}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                      <span className="rounded-full bg-accent px-2.5 py-0.5 font-semibold text-accent-foreground">
                        {t.subject}
                      </span>
                      <span className="text-muted-foreground">
                        Created {relativeTime(t.createdAt)}
                      </span>
                      {t.assignedTeacher && (
                        <span className="text-muted-foreground">
                          · Teacher: <span className="font-semibold text-foreground">{t.assignedTeacher}</span>
                        </span>
                      )}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </main>

        <RaiseTicketDialog open={openDialog} onOpenChange={setOpenDialog} />
      </div>
    </TooltipProvider>
  );
}
