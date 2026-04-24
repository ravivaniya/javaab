import { useEffect, useRef, useState } from "react";
import type { InputMode, StudyStruggle } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface StruggleStepProps {
  value?: StudyStruggle;
  inputMode?: InputMode;
  onSelectStruggle: (s: StudyStruggle) => void;
  onSelectInput: (m: InputMode) => void;
}

const STRUGGLES: { id: StudyStruggle; label: string; emoji: string }[] = [
  { id: "forget_later", label: "I understand in class but forget later", emoji: "🧠" },
  { id: "dont_understand", label: "I don't understand the concept at all", emoji: "🤔" },
  { id: "cant_solve", label: "I understand it but can't solve numericals or problems", emoji: "🧮" },
  { id: "cant_write", label: "I know it but can't write proper exam answers", emoji: "✍️" },
  { id: "run_out_of_time", label: "I run out of time in exams", emoji: "⏱️" },
];

const INPUT_MODES: { id: InputMode; label: string; emoji: string; comingSoon?: boolean }[] = [
  { id: "type", label: "I'll type my doubts", emoji: "⌨️" },
  { id: "photo", label: "I'll photograph my textbook / notebook", emoji: "📸" },
  { id: "voice", label: "I'd prefer to speak", emoji: "🎙️", comingSoon: true },
];

/** Onboarding Step 5 — biggest struggle + preferred input mode. */
export function StruggleStep({
  value,
  inputMode,
  onSelectStruggle,
  onSelectInput,
}: StruggleStepProps) {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
          What's your biggest struggle while studying?
        </h2>
        <p className="text-muted-foreground">Pick the one that fits most.</p>
      </header>

      <div className="flex flex-col gap-2">
        {STRUGGLES.map((s) => {
          const active = value === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => onSelectStruggle(s.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-3xl border-2 bg-card px-4 py-3.5 text-left transition-all hover:-translate-y-0.5 hover:shadow-soft",
                active ? "border-primary bg-primary/5 shadow-soft" : "border-border",
              )}
              aria-pressed={active}
            >
              <span className="text-2xl" aria-hidden>{s.emoji}</span>
              <span className="font-medium">{s.label}</span>
            </button>
          );
        })}
      </div>

      <InputModeSlot
        open={value !== undefined}
        inputMode={inputMode}
        onSelect={onSelectInput}
      />
    </div>
  );
}

function InputModeSlot({
  open,
  inputMode,
  onSelect,
}: {
  open: boolean;
  inputMode?: InputMode;
  onSelect: (m: InputMode) => void;
}) {
  const innerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (!open) {
      setHeight(0);
      return;
    }
    const update = () =>
      innerRef.current && setHeight(innerRef.current.scrollHeight);
    update();
    // Re-measure when input mode chips re-render (selected state changes size slightly).
    const ro = innerRef.current ? new ResizeObserver(update) : null;
    if (innerRef.current && ro) ro.observe(innerRef.current);
    return () => ro?.disconnect();
  }, [open, inputMode]);

  return (
    <div
      style={{ height }}
      className="overflow-hidden transition-[height] duration-200 ease-in-out"
      aria-hidden={!open}
    >
      <div ref={innerRef} className="pt-2">
        <div className="rounded-3xl border-2 border-dashed border-border bg-secondary/40 p-4">
          <p className="mb-3 text-sm font-medium">
            How do you prefer to ask Javaab questions?
          </p>
          <div className="flex flex-wrap gap-2">
            {INPUT_MODES.map((m) => {
              const active = inputMode === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => onSelect(m.id)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-pill border-2 px-4 py-2 text-sm font-semibold transition-all",
                    active
                      ? "border-primary bg-primary text-primary-foreground shadow-glow"
                      : "border-border bg-card hover:border-primary/40",
                  )}
                >
                  <span aria-hidden>{m.emoji}</span>
                  <span>{m.label}</span>
                  {m.comingSoon ? (
                    <Badge
                      variant="secondary"
                      className={cn(
                        "ml-1 text-[10px]",
                        active && "bg-primary-foreground/20 text-primary-foreground",
                      )}
                    >
                      Coming soon
                    </Badge>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
