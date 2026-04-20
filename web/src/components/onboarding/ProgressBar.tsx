interface ProgressBarProps {
  current: number; // 1-based
  total: number;
}

/** Top progress bar that fills orange as onboarding steps complete. */
export function ProgressBar({ current, total }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (current / total) * 100));
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
        <span>Step {current} of {total}</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full overflow-hidden rounded-full bg-secondary"
      >
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
