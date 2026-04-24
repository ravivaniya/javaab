interface Props {
  /** Friendly model label shown below the dots, e.g. "GPT-4.1 Mini". */
  modelHint?: string;
}

/** Three bouncing orange dots for AI typing indicator, with optional model hint. */
export function TypingDots({ modelHint }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 px-1 py-2">
        <span className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary" style={{ animationDelay: "0s" }} />
        <span className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary" style={{ animationDelay: "0.15s" }} />
        <span className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary" style={{ animationDelay: "0.3s" }} />
      </div>
      {modelHint && (
        <p className="px-1 text-[11px] text-muted-foreground">
          Thinking with {modelHint}...
        </p>
      )}
    </div>
  );
}
