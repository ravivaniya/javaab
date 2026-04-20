import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ThumbsDown, ThumbsUp } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/tickets/StatusBadge";
import { Markdown } from "@/components/chat/Markdown";
import { useAuth } from "@/hooks/useAuth";
import { getTicket, relativeTime, type Ticket } from "@/lib/tickets";
import { useToast } from "@/hooks/use-toast";

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const { toast } = useToast();
  const [ticket, setTicket] = useState<Ticket | undefined>();

  useEffect(() => {
    if (!user || !id) return;
    const sync = () => setTicket(getTicket(user.phone, id));
    sync();
    window.addEventListener("javaab:tickets", sync);
    const poll = setInterval(sync, 2000);
    return () => {
      window.removeEventListener("javaab:tickets", sync);
      clearInterval(poll);
    };
  }, [user, id]);

  if (!ticket) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader showBack />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center">
          <p className="font-display text-2xl font-black">Ticket not found</p>
          <Button onClick={() => nav("/tickets")} variant="ghost" className="mt-4">
            <ArrowLeft className="h-4 w-4" />
            Back to tickets
          </Button>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
        <Link
          to="/tickets"
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          All tickets
        </Link>

        {/* Question card */}
        <article className="rounded-3xl bg-card p-6 ring-1 ring-border sm:p-7">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span className="font-mono font-semibold tracking-wide">{ticket.id}</span>
            <StatusBadge status={ticket.status} />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-accent px-2.5 py-0.5 font-semibold text-accent-foreground">
              {ticket.subject}
            </span>
            <span className="text-muted-foreground">
              Created {relativeTime(ticket.createdAt)}
            </span>
          </div>

          <h1 className="mt-4 font-display text-2xl font-black leading-snug sm:text-3xl">
            {ticket.question}
          </h1>

          {ticket.imageUrl && (
            <img
              src={ticket.imageUrl}
              alt="Question attachment"
              className="mt-4 max-h-80 rounded-2xl object-cover ring-1 ring-border"
            />
          )}
        </article>

        {/* AI attempt */}
        {ticket.aiAttempt && (
          <section className="mt-5 rounded-3xl bg-muted/50 p-5 ring-1 ring-border">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              AI attempted but wasn't confident enough
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground/80">
              {ticket.aiAttempt}
            </p>
          </section>
        )}

        {/* Teacher answer */}
        {ticket.status === "answered" && ticket.answer ? (
          <section className="mt-5 rounded-3xl bg-card p-6 ring-1 ring-border sm:p-7">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/15 text-lg">
                🎓
              </div>
              <div>
                <p className="text-sm font-bold">
                  Answered by {ticket.assignedTeacher ?? "Verified Teacher"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {ticket.teacherCredentials} ·{" "}
                  {ticket.answeredAt ? relativeTime(ticket.answeredAt) : ""}
                </p>
              </div>
            </div>

            <Markdown>{ticket.answer}</Markdown>

            <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toast({ title: "Thanks for your feedback!" })}
                  className="h-8 px-2 text-muted-foreground hover:text-success"
                  aria-label="Helpful"
                >
                  <ThumbsUp className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toast({ title: "Thanks — we'll review this." })}
                  className="h-8 px-2 text-muted-foreground hover:text-destructive"
                  aria-label="Not helpful"
                >
                  <ThumbsDown className="h-4 w-4" />
                </Button>
              </div>

              {ticket.savedToCache && (
                <span className="rounded-full bg-success/10 px-3 py-1 text-xs font-semibold text-success">
                  ✅ Saved to Javaab's knowledge base
                </span>
              )}
            </div>
          </section>
        ) : (
          <section className="mt-5 flex items-center gap-3 rounded-3xl border border-dashed border-border bg-card/60 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-warning/15">
              ⏳
            </div>
            <div>
              <p className="font-semibold">
                {ticket.status === "open"
                  ? "Queued for assignment"
                  : `${ticket.assignedTeacher ?? "A teacher"} is reviewing your question`}
              </p>
              <p className="text-sm text-muted-foreground">
                You'll be notified when the answer arrives. Most tickets are answered within 24 hours.
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
