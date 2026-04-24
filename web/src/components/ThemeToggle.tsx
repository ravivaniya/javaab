import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Props {
  /** When true, renders a labelled segmented control (used in Settings). */
  variant?: "icon" | "segmented";
  className?: string;
}

const OPTIONS: { value: "light" | "dark" | "system"; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

/** Theme switcher. `icon` is a compact dropdown for headers; `segmented` is a row of pills for Settings. */
export function ThemeToggle({ variant = "icon", className }: Props) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (variant === "segmented") {
    return (
      <div
        role="radiogroup"
        aria-label="Theme"
        className={cn(
          "inline-flex w-full rounded-pill border border-border bg-muted/40 p-1",
          className,
        )}
      >
        {OPTIONS.map(({ value, label, Icon }) => {
          const active = mounted && theme === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setTheme(value)}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 rounded-pill px-3 py-2 text-sm font-semibold transition-colors",
                active
                  ? "bg-card text-foreground shadow-soft"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </button>
          );
        })}
      </div>
    );
  }

  const Icon = mounted && resolvedTheme === "dark" ? Moon : Sun;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground outline-none ring-offset-background transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
        aria-label="Toggle theme"
      >
        <Icon className="h-[18px] w-[18px]" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40 rounded-2xl">
        {OPTIONS.map(({ value, label, Icon: OptIcon }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => setTheme(value)}
            className={cn(
              "cursor-pointer",
              theme === value && "font-semibold text-foreground",
            )}
          >
            <OptIcon className="h-4 w-4" /> {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
