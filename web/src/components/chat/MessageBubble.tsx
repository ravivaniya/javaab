import { useState } from "react";
import { BookOpen, ChevronDown, ThumbsDown, ThumbsUp, ShieldCheck, Sparkles, AlertTriangle } from "lucide-react";
import { ChatMessage } from "@/lib/chat";
import { Markdown } from "./Markdown";
import { TypingDots } from "./TypingDots";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface Props {
  message: ChatMessage;
}

const CONFIDENCE_META = {
  verified: {
    label: "Verified",
    Icon: ShieldCheck,
    className: "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]",
  },
  ai: {
    label: "AI Generated",
    Icon: Sparkles,
    className: "bg-accent text-accent-foreground",
  },
  low: {
    label: "Low Confidence",
    Icon: AlertTriangle,
    className: "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))]",
  },
} as const;

export function MessageBubble({ message }: Props) {
  const [showSource, setShowSource] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  if (message.role === "user") {
    return (
      <div className="flex w-full justify-end">
        <div className="max-w-[85%] space-y-2 rounded-3xl rounded-tr-md bg-primary/10 px-5 py-3 text-foreground sm:max-w-[75%]">
          {message.imageUrl && (
            <img
              src={message.imageUrl}
              alt="Attached"
              className="max-h-60 rounded-2xl object-cover"
            />
          )}
          <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{message.content}</p>
        </div>
      </div>
    );
  }

  const meta = CONFIDENCE_META[message.confidence ?? "ai"];
  const hasContent = message.content.trim().length > 0;

  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[92%] space-y-3 rounded-3xl rounded-tl-md bg-card px-5 py-4 shadow-sm ring-1 ring-border/50 sm:max-w-[80%]">
        {!hasContent ? <TypingDots /> : <Markdown>{message.content}</Markdown>}

        {hasContent && (
          <>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {message.source && (
                <button
                  onClick={() => setShowSource((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/70"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  Source
                  <ChevronDown
                    className={cn("h-3.5 w-3.5 transition-transform", showSource && "rotate-180")}
                  />
                </button>
              )}

              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                  meta.className,
                )}
              >
                <meta.Icon className="h-3.5 w-3.5" />
                {meta.label}
              </span>

              <div className="ml-auto flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn("h-7 w-7", feedback === "up" && "text-primary")}
                  onClick={() => setFeedback(feedback === "up" ? null : "up")}
                  aria-label="Helpful"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn("h-7 w-7", feedback === "down" && "text-destructive")}
                  onClick={() => setFeedback(feedback === "down" ? null : "down")}
                  aria-label="Not helpful"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            {showSource && message.source && (
              <div className="rounded-2xl border border-dashed border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground animate-fade-in">
                <p className="font-semibold text-foreground">{message.source.book}</p>
                <p>{message.source.chapter}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
