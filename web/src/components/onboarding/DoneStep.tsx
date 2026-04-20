import { ArrowRight, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Confetti } from "./Confetti";
import type { Board, Lang, StudyStruggle } from "@/lib/auth";

interface DoneStepProps {
  board: Board;
  classNum: number;
  languages: Lang[];
  struggle?: StudyStruggle;
  onPrimary: () => void;
  onSecondary: () => void;
}

const boardLabel: Record<Board, string> = {
  cbse: "CBSE",
  gseb: "GSEB",
};
const langLabel: Record<Lang, string> = {
  en: "English",
  hi: "हिन्दी",
  gu: "ગુજરાતી",
};

const STRUGGLE_LINE: Record<StudyStruggle, string> = {
  forget_later: "I'll help you revise smarter, not harder.",
  dont_understand: "I'll explain every concept from the ground up.",
  cant_solve: "Step-by-step solutions — that's what I do best.",
  cant_write: "I'll show you exactly how to write exam-ready answers.",
  run_out_of_time: "Quick, sharp answers. No fluff. Let's go.",
};

/** Onboarding Step 6 — celebration + personalised summary. */
export function DoneStep({
  board,
  classNum,
  languages,
  struggle,
  onPrimary,
  onSecondary,
}: DoneStepProps) {
  const personalLine = struggle ? STRUGGLE_LINE[struggle] : "Let's get started.";

  return (
    <div className="relative space-y-6 text-center">
      <Confetti />

      <div className="relative space-y-3">
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-primary text-4xl shadow-glow">
          🎉
        </div>
        <h2 className="font-display text-4xl font-black tracking-tight sm:text-5xl">
          Welcome to Javaab! 🎉
        </h2>
        <p className="mx-auto max-w-md text-lg text-foreground/80">{personalLine}</p>
      </div>

      <div className="relative flex flex-wrap justify-center gap-2">
        <SummaryChip>{boardLabel[board]}</SummaryChip>
        <SummaryChip>Class {classNum}</SummaryChip>
        {languages.map((l) => (
          <SummaryChip key={l}>{langLabel[l]}</SummaryChip>
        ))}
      </div>

      <div className="relative flex flex-col gap-3 sm:flex-row">
        <Button
          size="lg"
          onClick={onPrimary}
          className="h-14 flex-1 rounded-pill text-base font-semibold shadow-glow"
        >
          Ask my first question <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
        <Button
          size="lg"
          variant="outline"
          onClick={onSecondary}
          className="h-14 flex-1 rounded-pill text-base font-semibold"
        >
          <BookOpen className="mr-1 h-4 w-4" /> Browse subjects first
        </Button>
      </div>
    </div>
  );
}

function SummaryChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-pill border border-border bg-secondary px-4 py-1.5 text-sm font-semibold">
      {children}
    </span>
  );
}
