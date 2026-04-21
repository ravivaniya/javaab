import { useMemo } from "react";
import { ChevronsLeft, ChevronsRight, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Conversation, bucketOf, DateBucket, formatChatTitle } from "@/lib/chat";
import { cn } from "@/lib/utils";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onCloseMobile?: () => void;
  /** When true, render the icon-only collapsed rail (desktop only). */
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const ORDER: DateBucket[] = ["Today", "Yesterday", "This Week", "Earlier"];

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onCloseMobile,
  collapsed = false,
  onToggleCollapse,
}: Props) {
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

  if (collapsed) {
    return (
      <aside className="flex h-full w-full flex-col items-center bg-sidebar py-3 text-sidebar-foreground">
        <Button
          size="icon"
          variant="ghost"
          aria-label="Expand sidebar"
          onClick={onToggleCollapse}
          className="mb-2 h-9 w-9"
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          aria-label="New chat"
          onClick={() => {
            onNew();
            onCloseMobile?.();
          }}
          className="h-9 w-9 rounded-full"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center justify-between gap-2 border-b border-sidebar-border p-3">
        <span className="px-1 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Chats
        </span>
        {onToggleCollapse && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Collapse sidebar"
            onClick={onToggleCollapse}
            className="hidden h-8 w-8 md:inline-flex"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
        )}
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
                      <li key={c.id} className="group relative">
                        <button
                          onClick={() => {
                            onSelect(c.id);
                            onCloseMobile?.();
                          }}
                          className={cn(
                            "flex w-full items-start gap-2 rounded-xl px-3 py-2 pr-10 text-left text-sm transition-colors",
                            "hover:bg-sidebar-accent",
                            isActive &&
                              "bg-sidebar-accent border-l-[3px] border-primary pl-[9px]",
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <p
                              className="truncate font-medium text-sidebar-foreground"
                              title={c.title}
                            >
                              {formatChatTitle(c.title)}
                            </p>
                            <span className="text-xs text-muted-foreground">
                              {relTime(c.updatedAt)}
                            </span>
                          </div>
                        </button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(c.id);
                          }}
                          className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground hover:bg-background hover:text-destructive focus-visible:text-destructive md:opacity-80 md:group-hover:opacity-100 md:group-focus-within:opacity-100"
                          aria-label="Delete chat"
                          title="Delete chat"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
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
    </aside>
  );
}

function relTime(ts: number): string {
  const d = new Date(ts);
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
