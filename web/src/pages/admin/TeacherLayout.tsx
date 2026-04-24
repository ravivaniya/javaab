import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  Building2,
  LayoutDashboard,
  LogOut,
  Menu,
  Ticket,
  BarChart,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

export default function TeacherLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    {
      label: "Dashboard",
      icon: LayoutDashboard,
      path: "/admin/teacher/dashboard",
    },
    { label: "Tickets", icon: Ticket, path: "/admin/teacher/tickets" },
    { label: "Analytics", icon: BarChart, path: "/admin/teacher/analytics" },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const SidebarContent = () => (
    <div className="flex h-full flex-col justify-between py-6 px-4">
      <div className="space-y-6">
        <div className="flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Building2 className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-lg font-bold leading-none tracking-tight">
              Javaab Admin
            </h1>
            <p className="mt-1 text-xs text-muted-foreground">Teacher Portal</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.path);
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="space-y-4 px-2">
        <div className="rounded-xl border border-border bg-muted/40 p-3">
          <p className="text-sm font-semibold">{user?.phone}</p>
          <p className="text-xs text-muted-foreground">Admin Access</p>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
          onClick={handleLogout}
        >
          <LogOut className="mr-3 h-5 w-5" />
          Logout
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full bg-background">
      {/* Desktop sidebar */}
      <div className="hidden h-full w-[280px] shrink-0 border-r border-border md:block">
        <SidebarContent />
      </div>

      {/* Main Container */}
      <div className="flex h-full min-w-0 flex-1 flex-col">
        {/* Mobile Header */}
        <header className="flex h-14 items-center gap-3 border-b border-border bg-card/60 px-4 backdrop-blur md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open menu"
                className="-ml-2"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] p-0">
              <SidebarContent />
            </SheetContent>
          </Sheet>
          <span className="font-display font-semibold">Teacher Portal</span>
        </header>

        {/* Dynamic View */}
        <main className="flex-1 overflow-y-auto bg-muted/20">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
