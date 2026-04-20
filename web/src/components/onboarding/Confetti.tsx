import { useMemo } from "react";

const COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--cbse))",
  "hsl(var(--plus))",
  "hsl(var(--success))",
  "hsl(var(--warning))",
];

/** CSS-only confetti burst. ~40 pieces, no JS animation loop. */
export function Confetti({ count = 40 }: { count?: number }) {
  const pieces = useMemo(
    () =>
      Array.from({ length: count }).map((_, i) => ({
        id: i,
        x: `${Math.random() * 100}vw`,
        drift: `${(Math.random() - 0.5) * 200}px`,
        delay: `${Math.random() * 0.6}s`,
        dur: `${2.5 + Math.random() * 2}s`,
        color: COLORS[i % COLORS.length],
        rotate: `${Math.random() * 360}deg`,
        size: 8 + Math.random() * 10,
      })),
    [count],
  );

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      {pieces.map((p) => (
        <span
          key={p.id}
          className="confetti-piece"
          style={{
            left: p.x,
            background: p.color,
            width: p.size,
            height: p.size * 1.4,
            transform: `rotate(${p.rotate})`,
            ["--x" as never]: "0px",
            ["--drift" as never]: p.drift,
            ["--delay" as never]: p.delay,
            ["--dur" as never]: p.dur,
          }}
        />
      ))}
    </div>
  );
}
