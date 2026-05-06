import { Check } from "lucide-react";
import type { Lang } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface LanguageStepProps {
  value: Lang[];
  onChange: (langs: Lang[]) => void;
}

const LANGS: { id: Lang; native: string; en: string; emoji: string }[] = [
  { id: "en", native: "English", en: "English", emoji: "🇬🇧" },
  { id: "hi", native: "हिन्दी", en: "Hindi", emoji: "🇮🇳" },
  { id: "gu", native: "ગુજરાતી", en: "Gujarati", emoji: "🪔" },
];

/** Onboarding Step 3 — multi-select study language. */
export function LanguageStep({ value, onChange }: LanguageStepProps) {
  const toggle = (l: Lang) => {
    onChange(value.includes(l) ? value.filter((x) => x !== l) : [...value, l]);
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
          Which language do you want to study in?
        </h2>
        <p className="text-muted-foreground">Pick one or more.</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        {LANGS.map((l) => {
          const active = value.includes(l.id);
          return (
            <button
              key={l.id}
              type="button"
              onClick={() => toggle(l.id)}
              className={cn(
                "relative flex flex-col items-start gap-2 rounded-3xl border-2 bg-card p-5 text-left transition-all hover:-translate-y-0.5 hover:shadow-soft",
                active ? "border-primary shadow-soft" : "border-border",
              )}
              aria-pressed={active}
            >
              <span className="text-3xl" aria-hidden>{l.emoji}</span>
              <div className="font-display text-xl font-bold">{l.native}</div>
              <div className="text-xs text-muted-foreground">{l.en}</div>
              {active ? (
                <span className="absolute right-3 top-3 grid h-6 w-6 place-items-center rounded-full bg-primary text-primary-foreground">
                  <Check className="h-3.5 w-3.5" />
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      <p className="rounded-2xl bg-accent px-4 py-3 text-sm text-accent-foreground">
        💡 Don't worry — you can type in <strong>any</strong> language and Javaab will understand!
      </p>
    </div>
  );
}
