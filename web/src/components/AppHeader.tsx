import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, Gift, LogOut, MessageSquare, Settings, Sparkles, Ticket } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
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
}

const NAV = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/subjects", label: "Subjects", icon: BookOpen },
  { to: "/tickets", label: "Tickets", icon: Ticket },
];

const PLAN_CLS: Record<string, string> = {
  free: "bg-muted text-muted-foreground",
  plus: "bg-[hsl(var(--plus))]/15 text-[hsl(var(--plus))]",
  pro:  "bg-[hsl(var(--pro))]/15 text-[hsl(var(--pro))]",
};

/** Top nav for the non-chat app pages (Subjects/Tickets/Refer/Settings). */
export function AppHeader({ showBack = false }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const planLabel = (user?.plan ?? "free").toUpperCase();
  const initials = user?.phone?.slice(-2) ?? "JV";
  const isFree = (user?.plan ?? "free") === "free";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          {showBack ? (
            <Link
              to="/chat"
              className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Link>
          ) : (
            <Logo />
          )}
        </div>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active = pathname === to || pathname.startsWith(`${to}/`);
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
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
              "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide",
              PLAN_CLS[user?.plan ?? "free"],
            )}
          >
            {planLabel}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 rounded-2xl">
              <DropdownMenuLabel className="font-normal">
                <p className="text-xs text-muted-foreground">Signed in as</p>
                <p className="font-semibold">+91 {user?.phone}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/settings" className="cursor-pointer">
                  <Settings className="h-4 w-4" /> Profile &amp; Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/settings/subscription" className="cursor-pointer">
                  <Settings className="h-4 w-4" /> Subscription
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/refer" className="cursor-pointer">
                  <Gift className="h-4 w-4" /> Refer & earn
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive focus:text-destructive">
                <LogOut className="h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Mobile bottom-style inline nav */}
      <nav className="flex items-center gap-1 border-t border-border px-3 py-2 md:hidden">
        {NAV.map(({ to, label, icon: Icon }) => {
          const active = pathname === to || pathname.startsWith(`${to}/`);
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 rounded-pill px-2 py-1.5 text-xs font-semibold transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
