import { Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "Explain photosynthesis",
  "Solve a quadratic equation",
  "Causes of the French Revolution",
  "Newton's three laws of motion",
];

interface Props {
  onPick: (text: string) => void;
  name?: string;
}

/** Center-aligned empty state with quick-start chips. */
export function QuickStartChips({ onPick, name }: Props) {
  const greeting = name?.trim() ? `Hi, ${name.trim()} 👋` : null;
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-3xl bg-primary/10 text-primary">
        <Sparkles className="h-7 w-7" />
      </div>
      {greeting && (
        <p className="mb-2 font-display text-lg font-bold text-primary">{greeting}</p>
      )}
      <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
        Sawaal kuch bhi ho. <span aria-hidden>📚</span>
      </h2>
      <p className="mt-2 max-w-md text-muted-foreground">
        Ask anything from your syllabus — in English, हिन्दी, or ગુજરાતી.
      </p>
      <div className="mt-8 flex max-w-2xl flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-pill border border-border bg-card px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-primary hover:shadow-md"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
