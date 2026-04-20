import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Plus, Settings, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/brand/Logo";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Conversation, bucketOf, DateBucket } from "@/lib/chat";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onCloseMobile?: () => void;
}

const ORDER: DateBucket[] = ["Today", "Yesterday", "This Week", "Earlier"];

const PLAN_BADGE: Record<string, { label: string; cls: string }> = {
  free: { label: "Free", cls: "bg-muted text-muted-foreground" },
  plus: { label: "Plus", cls: "bg-[hsl(var(--plus))]/15 text-[hsl(var(--plus))]" },
  pro: { label: "Pro", cls: "bg-[hsl(var(--pro))]/15 text-[hsl(var(--pro))]" },
};

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onCloseMobile,
}: Props) {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const grouped = useMemo(() => {
    const out: Record<DateBucket, Conversation[]> = {
      Today: [],
      Yesterday: [],
      "This Week": [],
      Earlier: [],
    };
    for (const c of conversations) out[bucketOf(c.updatedAt)].push(c);
    return out;
  }, [conversations]);

  const badge = PLAN_BADGE[user?.plan ?? "free"];
  const initials = user?.phone?.slice(-2) ?? "JV";

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-sidebar-border p-4">
        <Logo />
      </div>

      <div className="p-3">
        <Button
          onClick={() => {
            onNew();
            onCloseMobile?.();
          }}
          className="w-full rounded-pill"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* History */}
      <ScrollArea className="flex-1 px-2">
        <div className="space-y-4 pb-4">
          {ORDER.map((bucket) => {
            const items = grouped[bucket];
            if (!items.length) return null;
            return (
              <div key={bucket}>
                <p className="px-2 pb-1 pt-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {bucket}
                </p>
                <ul className="space-y-0.5">
                  {items.map((c) => {
                    const isActive = c.id === activeId;
                    return (
                      <li key={c.id}>
                        <button
                          onClick={() => {
                            onSelect(c.id);
                            onCloseMobile?.();
                          }}
                          className={cn(
                            "group relative flex w-full items-start gap-2 rounded-xl px-3 py-2 text-left text-sm transition-colors",
                            "hover:bg-sidebar-accent",
                            isActive &&
                              "bg-sidebar-accent border-l-[3px] border-primary pl-[9px]",
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-medium text-sidebar-foreground">
                              {c.title}
                            </p>
                            <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                              {c.subject && (
                                <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium">
                                  {c.subject}
                                </span>
                              )}
                              <span>{relTime(c.updatedAt)}</span>
                            </div>
                          </div>
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={(e) => {
                              e.stopPropagation();
                              onDelete(c.id);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.stopPropagation();
                                onDelete(c.id);
                              }
                            }}
                            className="invisible mt-0.5 rounded-md p-1 text-muted-foreground hover:bg-background hover:text-destructive group-hover:visible"
                            aria-label="Delete chat"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}

          {conversations.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              No chats yet. Start a new one!
            </p>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-3 rounded-2xl px-2 py-2">
          <Avatar className="h-9 w-9">
            <AvatarFallback className="bg-primary/10 text-primary font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">+91 {user?.phone}</p>
            <span
              className={cn(
                "inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                badge.cls,
              )}
            >
              {badge.label}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => nav("/settings/subscription")}
            aria-label="Settings"
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={logout}
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}

function relTime(ts: number): string {
  const d = new Date(ts);
  const now = Date.now();
  const diff = now - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
