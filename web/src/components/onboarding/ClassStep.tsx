import { useEffect, useRef, useState } from "react";
import type { Board, DifficultSubject } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface ClassStepProps {
  board?: Board;
  value?: number;
  difficultSubjects: DifficultSubject[];
  onSelectClass: (c: number) => void;
  onChangeSubjects: (s: DifficultSubject[]) => void;
}

const CLASSES = [6, 7, 8, 9, 10, 11, 12];

const SUBJECTS: { id: DifficultSubject; label: string; emoji: string; boards?: Board[] }[] = [
  { id: "maths", label: "Maths", emoji: "📐" },
  { id: "science", label: "Science", emoji: "🔬" },
  { id: "social", label: "Social Science", emoji: "🌍" },
  { id: "english", label: "English", emoji: "📚" },
  { id: "hindi", label: "Hindi", emoji: "📝", boards: ["cbse"] },
  { id: "gujarati", label: "Gujarati", emoji: "✏️", boards: ["gseb"] },
];

/** Onboarding Step 2 — class + difficult subjects sub-question. */
export function ClassStep({
  board,
  value,
  difficultSubjects,
  onSelectClass,
  onChangeSubjects,
}: ClassStepProps) {
  const subjects = SUBJECTS.filter((s) => !s.boards || (board && s.boards.includes(board)));

  const toggleSubject = (id: DifficultSubject) => {
    onChangeSubjects(
      difficultSubjects.includes(id)
        ? difficultSubjects.filter((x) => x !== id)
        : [...difficultSubjects, id],
    );
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-3xl font-black tracking-tight sm:text-4xl">
          Which class are you in?
        </h2>
        <p className="text-muted-foreground">Tap your current class.</p>
      </header>

      <div className="flex flex-wrap gap-3">
        {CLASSES.map((c) => {
          const active = value === c;
          return (
            <button
              key={c}
              type="button"
              onClick={() => onSelectClass(c)}
              className={cn(
                "h-14 min-w-[64px] rounded-pill border-2 px-6 text-lg font-bold transition-all",
                active
                  ? "border-primary bg-primary text-primary-foreground shadow-glow"
                  : "border-border bg-card text-foreground hover:border-primary/40",
              )}
              aria-pressed={active}
            >
              {c}
            </button>
          );
        })}
      </div>

      <SubjectsSlot
        open={value !== undefined}
        subjects={subjects}
        selected={difficultSubjects}
        onToggle={toggleSubject}
      />
    </div>
  );
}

function SubjectsSlot({
  open,
  subjects,
  selected,
  onToggle,
}: {
  open: boolean;
  subjects: { id: DifficultSubject; label: string; emoji: string }[];
  selected: DifficultSubject[];
  onToggle: (id: DifficultSubject) => void;
}) {
  const innerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (open && innerRef.current) {
      const update = () => setHeight(innerRef.current!.scrollHeight);
      update();
      const ro = new ResizeObserver(update);
      ro.observe(innerRef.current);
      return () => ro.disconnect();
    }
    setHeight(0);
  }, [open, selected.length]);

  return (
    <div
      style={{ height }}
      className="overflow-hidden transition-[height] duration-200 ease-in-out"
      aria-hidden={!open}
    >
      <div ref={innerRef} className="pt-2">
        <div className="rounded-3xl border-2 border-dashed border-border bg-secondary/40 p-4">
          <p className="mb-1 text-sm font-medium">
            Which subjects do you find most difficult?
          </p>
          <p className="mb-3 text-xs text-muted-foreground">Optional — pick any that apply.</p>
          <div className="flex flex-wrap gap-2">
            {subjects.map((s) => {
              const active = selected.includes(s.id);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onToggle(s.id)}
                  className={cn(
                    "rounded-pill border-2 px-4 py-2 text-sm font-semibold transition-all",
                    active
                      ? "border-primary bg-primary/10 text-foreground"
                      : "border-border bg-card hover:border-primary/40",
                  )}
                  aria-pressed={active}
                >
                  <span className="mr-1.5" aria-hidden>{s.emoji}</span>
                  {s.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
