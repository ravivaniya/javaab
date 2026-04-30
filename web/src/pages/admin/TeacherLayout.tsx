import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  LayoutDashboard,
  LogOut,
  Menu,
  Ticket,
  BarChart,
  FileText,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AppHeader } from "@/components/AppHeader";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/admin/teacher/dashboard" },
  { label: "Tickets", icon: Ticket, path: "/admin/teacher/tickets" },
  { label: "Analytics", icon: BarChart, path: "/admin/teacher/analytics" },
  { label: "Question Papers", icon: FileText, path: "/admin/teacher/papers" },
  { label: "DPPs & Worksheets", icon: ClipboardList, path: "/admin/teacher/worksheets" },
];

export default function TeacherLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  /** Single nav button — icon-only with tooltip when the sidebar is collapsed. */
  const NavItem = ({ item }: { item: (typeof navItems)[0] }) => {
    const Icon = item.icon;
    const active = location.pathname.startsWith(item.path);
    const btn = (
      <button
        onClick={() => navigate(item.path)}
        className={`flex w-full items-center rounded-2xl px-3 py-3 text-sm font-medium transition-colors ${
          collapsed ? "justify-center" : "gap-3"
        } ${
          active
            ? "bg-[#FC8019]/10 text-[#FC8019] font-bold"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        }`}
      >
        <Icon className="h-5 w-5 shrink-0" />
        {!collapsed && <span>{item.label}</span>}
      </button>
    );
    if (collapsed) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>{btn}</TooltipTrigger>
          <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
      );
    }
    return btn;
  };

  const DesktopSidebar = () => (
    <div className="flex h-full flex-col py-3">
      {/* Collapse toggle */}
      <div className={`flex px-2 pb-2 ${collapsed ? "justify-center" : "justify-end"}`}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => setCollapsed((v) => !v)}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {collapsed ? "Expand" : "Collapse"}
          </TooltipContent>
        </Tooltip>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 px-2">
        {!collapsed && (
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Admin
          </p>
        )}
        {navItems.map((item) => (
          <NavItem key={item.path} item={item} />
        ))}
      </nav>

      {/* Logout */}
      <div className="px-2 pt-3">
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="w-full text-muted-foreground"
                onClick={handleLogout}
              >
                <LogOut className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Logout</TooltipContent>
          </Tooltip>
        ) : (
          <Button
            variant="ghost"
            className="w-full justify-start text-muted-foreground"
            onClick={handleLogout}
          >
            <LogOut className="mr-3 h-5 w-5" />
            Logout
          </Button>
        )}
      </div>
    </div>
  );

  /** Mobile drawer — always full-width. */
  const MobileSidebarContent = () => (
    <div className="flex h-full flex-col py-6 px-4">
      <p className="mb-4 px-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        Admin Portal
      </p>
      <nav className="flex-1 space-y-1">
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
              className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors ${
                active
                  ? "bg-[#FC8019]/10 text-[#FC8019] font-bold"
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
  );

  /** Mobile Sheet trigger — only renders on small screens. */
  const mobileTrigger = (
    <div className="md:hidden">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="Open menu" className="-ml-2">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[280px] p-0">
          <MobileSidebarContent />
        </SheetContent>
      </Sheet>
    </div>
  );

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Shared top header — Logo + nav links + Admin link + user avatar */}
      <AppHeader leftSlot={mobileTrigger} />

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar — nav only, no duplicate logo/user info */}
        <div
          className={`hidden h-full shrink-0 border-r border-border transition-all duration-300 ease-in-out md:block ${
            collapsed ? "w-16" : "w-[240px]"
          }`}
        >
          <DesktopSidebar />
        </div>

        <main className="flex-1 overflow-y-auto bg-muted/20">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
