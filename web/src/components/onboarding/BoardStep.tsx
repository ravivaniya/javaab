import { useEffect, useRef, useState } from "react";
import type { Board } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface BoardStepProps {
  value?: Board;
  attendsCoaching?: boolean;
  onSelectBoard: (b: Board) => void;
  onSelectCoaching: (attends: boolean) => void;
}

const boards: { id: Board; title: string; subtitle: string; accent: string; emoji: string }[] = [
  { id: "cbse", title: "CBSE (NCERT)", subtitle: "Class 6–12 · English + Hindi", accent: "cbse", emoji: "📘" },
  { id: "gseb", title: "Gujarat Board (GSEB)", subtitle: "Std 6–12 · Gujarati + English", accent: "gseb", emoji: "📕" },
];

/** Onboarding Step 1 — board + coaching sub-question. */
export function BoardStep({ value, attendsCoaching, onSelectBoard, onSelectCoaching }: BoardStepProps) {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
          Which board do you study in?
        </h2>
        <p className="text-muted-foreground">Pick one — you can change this later.</p>
      </header>

      <div className="grid gap-4">
        {boards.map((b) => {
          const active = value === b.id;
          return (
            <div key={b.id}>
              <button
                type="button"
                onClick={() => onSelectBoard(b.id)}
                className={cn(
                  "group relative flex w-full items-center gap-4 rounded-3xl border-2 bg-card p-5 text-left transition-all hover:-translate-y-0.5 hover:shadow-soft sm:p-6",
                  active ? "border-primary bg-primary/5 shadow-soft" : "border-black/5",
                )}
              >
                <div
                  className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-2xl"
                  style={{
                    backgroundColor: `hsl(var(--${b.accent}) / 0.12)`,
                    color: `hsl(var(--${b.accent}))`,
                  }}
                  aria-hidden
                >
                  {b.emoji}
                </div>
                <div className="flex-1">
                  <div className="font-display text-xl font-bold">{b.title}</div>
                  <div className="text-sm text-muted-foreground">{b.subtitle}</div>
                </div>
                <span
                  className={cn(
                    "h-5 w-5 shrink-0 rounded-full border-2",
                    active ? "border-primary bg-primary" : "border-border",
                  )}
                  aria-hidden
                />
              </button>

              <CoachingSlot
                open={active}
                attendsCoaching={attendsCoaching}
                onSelect={onSelectCoaching}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CoachingSlot({
  open,
  attendsCoaching,
  onSelect,
}: {
  open: boolean;
  attendsCoaching?: boolean;
  onSelect: (v: boolean) => void;
}) {
  const innerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (open && innerRef.current) {
      setHeight(innerRef.current.scrollHeight);
    } else {
      setHeight(0);
    }
  }, [open]);

  return (
    <div
      style={{ height }}
      className="overflow-hidden transition-[height] duration-200 ease-in-out"
      aria-hidden={!open}
    >
      <div ref={innerRef} className="pt-4">
        <div className="rounded-3xl border-2 border-dashed border-border bg-secondary/40 p-4">
          <p className="mb-3 text-sm font-medium">
            Do you attend a coaching class or tuition?
          </p>
          <div className="flex flex-wrap gap-2">
            <Chip selected={attendsCoaching === true} onClick={() => onSelect(true)}>
              ✅ Yes, I do
            </Chip>
            <Chip selected={attendsCoaching === false} onClick={() => onSelect(false)}>
              📚 No, I study on my own
            </Chip>
          </div>
        </div>
      </div>
    </div>
  );
}

function Chip({
  selected,
  children,
  onClick,
}: {
  selected: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-pill border-2 px-4 py-2 text-sm font-semibold transition-all",
        selected
          ? "border-primary bg-primary text-primary-foreground shadow-glow"
          : "border-border bg-card hover:border-primary/40",
      )}
    >
      {children}
    </button>
  );
}
