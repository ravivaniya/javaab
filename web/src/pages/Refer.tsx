import { useMemo, useState } from "react";
import { Copy, Crown, Gift, Share2, Trophy, Users } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/hooks/useAuth";
import {
  getCode,
  getLeaderboard,
  getReferralUrl,
  getReferrals,
  getStats,
  maskName,
  statusLabel,
} from "@/lib/referrals";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

const STEPS = [
  { n: 1, t: "Share your code", d: "Send your unique link to friends." },
  { n: 2, t: "Friend signs up", d: "They join Javaab using your link." },
  { n: 3, t: "Both earn 50 questions", d: "After they ask 5 questions, you both get the bonus." },
];

const STATUS_CLS: Record<string, string> = {
  signed_up: "bg-muted text-muted-foreground",
  completed_5: "bg-warning/15 text-warning",
  rewarded: "bg-success/15 text-success",
};

export default function Refer() {
  const { user } = useAuth();
  const code = useMemo(() => getCode(user?.phone), [user?.phone]);
  const url = getReferralUrl(code);
  const refs = useMemo(() => getReferrals(), []);
  const stats = useMemo(() => getStats(), []);
  const leaderboard = useMemo(() => getLeaderboard(), []);
  const [showLeaderboard, setShowLeaderboard] = useState(false);

  const milestone = stats.thisMonth >= 5 ? 10 : 5;
  const reward = milestone === 5 ? "1 month Plus FREE" : "1 month Pro FREE";
  const progress = Math.min(100, (stats.thisMonth / milestone) * 100);

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied!", description: label });
  };

  const share = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Try Javaab — your AI study buddy",
          text: `Use my code ${code} and we both get 50 bonus questions!`,
          url,
        });
      } catch {
        /* cancelled */
      }
    } else {
      copy(url, "Referral link");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Hero */}
        <header className="mb-8 text-center">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-pill bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
            <Gift className="h-3.5 w-3.5" />
            Refer & earn
          </div>
          <h1 className="font-display text-4xl font-black leading-[1.05] sm:text-5xl">
            Help a friend.<br className="sm:hidden" /> Earn free questions.
          </h1>
          <p className="mx-auto mt-3 max-w-md text-muted-foreground">
            Share Javaab with friends. When they ask their first 5 questions, you both
            get <strong className="text-foreground">50 bonus questions</strong>.
          </p>
        </header>

        {/* Code + share card */}
        <section className="mb-8 overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-soft sm:p-8">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Your referral code
          </p>
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="font-display text-5xl font-black tracking-tight text-primary sm:text-6xl">
              {code}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => copy(code, "Referral code")}
                className="rounded-pill"
              >
                <Copy className="h-4 w-4" /> Copy code
              </Button>
              <Button onClick={share} className="rounded-pill">
                <Share2 className="h-4 w-4" /> Share link
              </Button>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-border bg-background/60 px-4 py-2.5 text-sm">
            <span className="truncate font-mono text-xs text-muted-foreground">{url}</span>
            <button
              onClick={() => copy(url, "Referral link")}
              className="ml-auto shrink-0 text-xs font-semibold text-primary hover:underline"
            >
              Copy
            </button>
          </div>
        </section>

        {/* How it works */}
        <section className="mb-8">
          <h2 className="mb-4 font-display text-xl font-black">How it works</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.n} className="rounded-2xl border border-border bg-card p-5">
                <div className="mb-2 grid h-8 w-8 place-items-center rounded-full bg-primary text-sm font-black text-primary-foreground">
                  {s.n}
                </div>
                <p className="font-display font-bold">{s.t}</p>
                <p className="mt-1 text-sm text-muted-foreground">{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Stats */}
        <section className="mb-8">
          <h2 className="mb-4 font-display text-xl font-black">Your stats</h2>
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              { label: "Referred", value: stats.referred, icon: Share2 },
              { label: "Joined", value: stats.joined, icon: Users },
              { label: "Bonus questions", value: stats.bonusQuestions, icon: Gift },
              { label: "This month", value: stats.thisMonth, icon: Trophy },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-border bg-card p-5">
                <Icon className="h-5 w-5 text-primary" />
                <p className="mt-3 font-display text-3xl font-black">{value}</p>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {label}
                </p>
              </div>
            ))}
          </div>

          {/* Milestone */}
          <div className="mt-4 rounded-2xl border border-border bg-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold">
                Refer {milestone} this month → get{" "}
                <span className="text-primary">{reward}</span>
              </p>
              <p className="text-xs font-bold text-muted-foreground">
                {stats.thisMonth} / {milestone}
              </p>
            </div>
            <Progress value={progress} className="mt-3 h-2" />
          </div>
        </section>

        {/* Referral history */}
        <section className="mb-8">
          <h2 className="mb-4 font-display text-xl font-black">Referral history</h2>
          <div className="overflow-hidden rounded-2xl border border-border bg-card">
            {refs.length === 0 ? (
              <p className="p-8 text-center text-sm text-muted-foreground">
                No referrals yet — share your code to get started.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Friend</th>
                    <th className="px-5 py-3 font-semibold">Joined</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {refs.map((r) => (
                    <tr key={r.id} className="border-t border-border">
                      <td className="px-5 py-3 font-semibold">{maskName(r.name)}</td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {new Date(r.joinedAt).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                        })}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={cn(
                            "rounded-pill px-2 py-0.5 text-[10px] font-bold uppercase",
                            STATUS_CLS[r.status],
                          )}
                        >
                          {statusLabel(r.status)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        {/* Leaderboard */}
        <section>
          <Collapsible open={showLeaderboard} onOpenChange={setShowLeaderboard}>
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center justify-between rounded-2xl border border-border bg-card p-5 text-left transition-colors hover:bg-muted/40">
                <div className="flex items-center gap-3">
                  <Crown className="h-5 w-5 text-warning" />
                  <div>
                    <p className="font-display font-bold">Monthly leaderboard</p>
                    <p className="text-xs text-muted-foreground">
                      Top referrers this month
                    </p>
                  </div>
                </div>
                <span className="text-xs font-semibold text-primary">
                  {showLeaderboard ? "Hide" : "Show"}
                </span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 overflow-hidden rounded-2xl border border-border bg-card">
              <ul>
                {leaderboard.map((row) => (
                  <li
                    key={row.rank}
                    className="flex items-center gap-4 border-b border-border px-5 py-3 last:border-0"
                  >
                    <span className="w-6 font-display text-lg font-black text-muted-foreground">
                      {row.rank}
                    </span>
                    <span className="flex-1 font-semibold">
                      {row.badge && <span className="mr-1.5">{row.badge}</span>}
                      {row.name}
                    </span>
                    <span className="font-display text-lg font-black text-primary">
                      {row.count}
                    </span>
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        </section>
      </main>
    </div>
  );
}
