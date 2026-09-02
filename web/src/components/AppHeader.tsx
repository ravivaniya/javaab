import { Link, useLocation } from "react-router-dom";
import { MessageCircle, FileText, BookOpen } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { widgetConfig } from "@/config/widget.config";
import { cn } from "@/lib/utils";

interface Props {
  showBack?: boolean;
  leftSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
}

const NAV_ITEMS = [
  { to: "/chat", label: "Chat", icon: MessageCircle, feature: "chat" as const },
  { to: "/question-paper", label: "Question Paper", icon: FileText, feature: "qpg" as const },
  { to: "/dpp", label: "DPP", icon: BookOpen, feature: "dpp" as const },
];

export function AppHeader({ showBack = false, leftSlot, rightSlot }: Props) {
  const { pathname } = useLocation();

  const visibleNav = NAV_ITEMS.filter(
    (item) => widgetConfig.features[item.feature],
  );

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur">
      <div className="mx-auto flex h-14 items-center justify-between gap-2 px-3 sm:gap-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          {leftSlot}
          {showBack ? (
            <Link
              to="/chat"
              className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              ← Back
            </Link>
          ) : (
            <Link to="/" aria-label="Home" className="shrink-0">
              <Logo />
            </Link>
          )}
        </div>

        {/* Desktop nav — only show enabled features */}
        {!showBack && visibleNav.length > 1 && (
          <nav className="hidden items-center gap-1 md:flex">
            {visibleNav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-sm font-medium transition-colors",
                  pathname.startsWith(to)
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-1.5 sm:gap-2">
          {rightSlot}
          <ThemeToggle className="hidden sm:inline-flex" />
        </div>
      </div>
    </header>
  );
}
