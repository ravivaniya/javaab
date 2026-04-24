import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Gift,
  LogOut,
  Settings,
  Sparkles,
  Ticket,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

interface Props {
  /** Show a back-to-chat link instead of the nav. */
  showBack?: boolean;
  /** Optional left-side slot (e.g. mobile sidebar trigger on /chat). */
  leftSlot?: React.ReactNode;
  /** Optional right-side slot before account controls. */
  rightSlot?: React.ReactNode;
}

const PLAN_CLS: Record<string, string> = {
  free: "bg-muted text-muted-foreground",
  plus: "bg-[hsl(var(--plus))]/15 text-[hsl(var(--plus))]",
  pro: "bg-[hsl(var(--pro))]/15 text-[hsl(var(--pro))]",
};

/** Single source of truth for the top header across every page. */
export function AppHeader({ showBack = false, leftSlot, rightSlot }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const planLabel = (user?.plan ?? "free").toUpperCase();
  const initials =
    (user?.name ?? "").trim().charAt(0).toUpperCase() ||
    user?.phone?.slice(-2) ||
    "JV";
  const isFree = (user?.plan ?? "free") === "free";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

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
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Back</span>
            </Link>
          ) : (
            <Link to="/chat" aria-label="Go to chat" className="shrink-0">
              <Logo />
            </Link>
          )}
        </div>

        {/* Tickets nav (single remaining secondary route) */}
        <nav className="hidden items-center gap-1 md:flex">
          <Link
            to="/tickets"
            className={cn(
              "flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-sm font-medium transition-colors",
              pathname === "/tickets" || pathname.startsWith("/tickets/")
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Ticket className="h-4 w-4" />
            Tickets
          </Link>
        </nav>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {rightSlot}
          <ThemeToggle className="hidden sm:inline-flex" />
          {isFree && (
            <Link
              to="/subscribe"
              className="hidden items-center gap-1 rounded-pill bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 sm:inline-flex"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Upgrade
            </Link>
          )}
          <span
            className={cn(
              "hidden rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide sm:inline-block",
              PLAN_CLS[user?.plan ?? "free"],
            )}
          >
            {planLabel}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring">
              <Avatar className="h-9 w-9 cursor-pointer">
                <AvatarFallback className="bg-primary text-sm font-black text-primary-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 rounded-2xl">
              <DropdownMenuLabel className="font-normal">
                <p className="text-xs text-muted-foreground">Signed in as</p>
                <p className="font-semibold">
                  {user?.name || `+91 ${user?.phone ?? ""}`}
                </p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/settings" className="cursor-pointer">
                  <Settings className="h-4 w-4" /> Profile &amp; Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/settings/subscription" className="cursor-pointer">
                  <Sparkles className="h-4 w-4" /> Subscription
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/tickets" className="cursor-pointer md:hidden">
                  <Ticket className="h-4 w-4" /> Tickets
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/refer" className="cursor-pointer">
                  <Gift className="h-4 w-4" /> Refer &amp; earn
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive"
              >
                <LogOut className="h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
