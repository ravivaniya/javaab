import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  variant?: "default" | "light";
}

/** Javaab wordmark. SVG so it scales crisp on any background. */
export function Logo({ className, variant = "default" }: LogoProps) {
  const ink = variant === "light" ? "hsl(0 0% 100%)" : "hsl(var(--foreground))";
  const orange = "hsl(var(--primary))";
  return (
    <div className={cn("inline-flex items-center gap-2", className)} aria-label="Javaab">
      <svg width="34" height="34" viewBox="0 0 34 34" fill="none" aria-hidden>
        <rect width="34" height="34" rx="10" fill={orange} />
        <path
          d="M11 10h12v3.2c0 4.4-2.4 7-6 7s-6-2.6-6-7V10z"
          fill="hsl(0 0% 100%)"
        />
        <circle cx="23" cy="23" r="3" fill="hsl(0 0% 100%)" />
      </svg>
      <span
        className="font-display text-xl font-black tracking-tight"
        style={{ color: ink }}
      >
        javaab
      </span>
    </div>
  );
}
