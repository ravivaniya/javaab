import type { StudyMethod } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface StudyMethodStepProps {
  value?: StudyMethod;
  onSelect: (m: StudyMethod) => void;
}

const METHODS: { id: StudyMethod; label: string; emoji: string }[] = [
  { id: "textbook", label: "From textbook directly", emoji: "📖" },
  { id: "notes", label: "From my class notes", emoji: "📓" },
  { id: "videos", label: "From YouTube / videos", emoji: "▶️" },
  { id: "coaching", label: "From coaching material", emoji: "🏫" },
];

/** Onboarding Step 4 — how do you usually study? */
export function StudyMethodStep({ value, onSelect }: StudyMethodStepProps) {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
          How do you usually study?
        </h2>
        <p className="text-muted-foreground">
          Be honest — this helps Javaab answer in the way that works best for you.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        {METHODS.map((m) => {
          const active = value === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => onSelect(m.id)}
              className={cn(
                "flex flex-col items-start gap-3 rounded-3xl border-2 bg-card p-5 text-left transition-all hover:-translate-y-0.5 hover:shadow-soft",
                active ? "border-primary bg-primary/5 shadow-soft" : "border-black/5",
              )}
              aria-pressed={active}
            >
              <span className="text-3xl" aria-hidden>{m.emoji}</span>
              <div className="font-display text-lg font-bold leading-tight">{m.label}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
