/** Three bouncing orange dots for AI typing indicator. */
export function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-2">
      <span
        className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary"
        style={{ animationDelay: "0s" }}
      />
      <span
        className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary"
        style={{ animationDelay: "0.15s" }}
      />
      <span
        className="dot-bounce inline-block h-2 w-2 rounded-full bg-primary"
        style={{ animationDelay: "0.3s" }}
      />
    </div>
  );
}
