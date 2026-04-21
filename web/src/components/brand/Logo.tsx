import { cn } from "@/lib/utils";
import logoSrc from "@/assets/logo.png";

interface LogoProps {
  className?: string;
  variant?: "default" | "light";
  hideWordmark?: boolean;
}

/** Javaab brand mark + wordmark. */
export function Logo({
  className,
  variant = "default",
  hideWordmark = false,
}: LogoProps) {
  const ink = variant === "light" ? "hsl(0 0% 100%)" : "hsl(var(--foreground))";
  return (
    <div
      className={cn("inline-flex items-center gap-2", className)}
      aria-label="Javaab"
    >
      <img
        src={logoSrc}
        alt=""
        width={34}
        height={34}
        className="h-9 w-9 rounded-xl object-contain"
      />
      {!hideWordmark && (
        <span
          className="font-display text-xl font-black tracking-tight"
          style={{ color: ink }}
        >
          Javaab
        </span>
      )}
    </div>
  );
}
