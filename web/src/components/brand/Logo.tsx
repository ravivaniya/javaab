import { cn } from "@/lib/utils";
import { widgetConfig } from "@/config/widget.config";
import defaultLogoSrc from "@/assets/logo.png";

interface LogoProps {
  className?: string;
  variant?: "default" | "light";
  hideWordmark?: boolean;
}

/** Institute logo + wordmark, driven by widget.config.ts. */
export function Logo({ className, variant = "default", hideWordmark = false }: LogoProps) {
  const ink = variant === "light" ? "hsl(0 0% 100%)" : "hsl(var(--foreground))";
  const { logo_url, name } = widgetConfig.institute;

  return (
    <div
      className={cn("inline-flex items-center gap-2", className)}
      aria-label={name}
    >
      <img
        src={logo_url ?? defaultLogoSrc}
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
          {name}
        </span>
      )}
    </div>
  );
}
