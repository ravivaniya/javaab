import { motion } from "framer-motion";
import { Progress } from "@/components/ui/progress";
import type { SubjectMeta, SubjectProgress } from "@/lib/subjects";
import { cn } from "@/lib/utils";

interface Props {
  subject: SubjectMeta;
  progress: SubjectProgress;
  onClick: () => void;
}

const ACCENT_RING: Record<SubjectMeta["accent"], string> = {
  cbse:    "ring-cbse/20 hover:ring-cbse/50",
  pro:     "ring-pro/20 hover:ring-pro/50",
  warning: "ring-warning/20 hover:ring-warning/50",
  plus:    "ring-plus/20 hover:ring-plus/50",
  primary: "ring-primary/20 hover:ring-primary/50",
  success: "ring-success/20 hover:ring-success/50",
};

const ACCENT_BG: Record<SubjectMeta["accent"], string> = {
  cbse:    "bg-cbse/10 text-cbse",
  pro:     "bg-pro/10 text-pro",
  warning: "bg-warning/10 text-warning",
  plus:    "bg-plus/10 text-plus",
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
};

const ACCENT_BAR: Record<SubjectMeta["accent"], string> = {
  cbse:    "[&>div]:bg-cbse",
  pro:     "[&>div]:bg-pro",
  warning: "[&>div]:bg-warning",
  plus:    "[&>div]:bg-plus",
  primary: "[&>div]:bg-primary",
  success: "[&>div]:bg-success",
};

const SPAN_CLS: Record<NonNullable<SubjectMeta["span"]>, string> = {
  default: "sm:col-span-2 lg:col-span-2",
  wide:    "sm:col-span-4 lg:col-span-4",
  tall:    "sm:col-span-2 lg:col-span-2 lg:row-span-2",
};

export function SubjectCard({ subject, progress, onClick }: Props) {
  const pct = progress.totalChapters
    ? Math.round((progress.exploredChapters / progress.totalChapters) * 100)
    : 0;
  const span = subject.span ?? "default";

  return (
    <motion.button
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      onClick={onClick}
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-3xl bg-card p-6 text-left ring-1 transition-all hover:shadow-soft",
        ACCENT_RING[subject.accent],
        SPAN_CLS[span],
      )}
    >
      {/* Decorative blob */}
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-40 blur-2xl transition-opacity group-hover:opacity-70",
          ACCENT_BG[subject.accent],
        )}
      />

      <div className="relative">
        <div
          className={cn(
            "mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl text-3xl",
            ACCENT_BG[subject.accent],
          )}
        >
          <span aria-hidden>{subject.icon}</span>
        </div>
        <h3 className="font-display text-2xl font-black leading-tight">
          {subject.name}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {progress.totalChapters} chapters · {progress.questionsAnswered} questions answered
        </p>
      </div>

      <div className="relative mt-6 space-y-1.5">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Progress</span>
          <span>{pct}%</span>
        </div>
        <Progress value={pct} className={cn("h-1.5", ACCENT_BAR[subject.accent])} />
      </div>
    </motion.button>
  );
}
