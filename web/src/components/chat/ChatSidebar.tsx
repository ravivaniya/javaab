import { useMemo, useRef, useState } from "react";
import { ChevronsLeft, ChevronsRight, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Conversation, bucketOf, DateBucket, formatChatTitle, CHAT_TITLE_MAX_LENGTH } from "@/lib/chat";
import { cn } from "@/lib/utils";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
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
  onRename,
  onCloseMobile,
  collapsed = false,
  onToggleCollapse,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

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

  function startEditing(conv: Conversation, e: React.MouseEvent | React.KeyboardEvent) {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditValue(conv.title);
    // Focus the input in the next tick after render
    setTimeout(() => inputRef.current?.select(), 0);
  }

  function commitEdit(convId: string, currentTitle: string) {
    const trimmed = editValue.trim().slice(0, CHAT_TITLE_MAX_LENGTH);
    if (trimmed && trimmed !== currentTitle) {
      onRename(convId, trimmed);
    }
    setEditingId(null);
  }

  function cancelEdit() {
    setEditingId(null);
  }

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
          onClick={() => { onNew(); onCloseMobile?.(); }}
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
          onClick={() => { onNew(); onCloseMobile?.(); }}
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
                    const isEditing = editingId === c.id;

                    return (
                      <li key={c.id} className="group relative">
                        {isEditing ? (
                          // ── Inline edit mode ──────────────────────────────
                          <div className="flex items-center gap-1 rounded-xl px-3 py-1.5 bg-sidebar-accent border-l-[3px] border-primary pl-[9px]">
                            <input
                              ref={inputRef}
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value.slice(0, CHAT_TITLE_MAX_LENGTH))}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") { e.preventDefault(); commitEdit(c.id, c.title); }
                                if (e.key === "Escape") cancelEdit();
                              }}
                              onBlur={() => commitEdit(c.id, c.title)}
                              className="min-w-0 flex-1 bg-transparent text-sm font-medium text-sidebar-foreground outline-none"
                              maxLength={CHAT_TITLE_MAX_LENGTH}
                              autoFocus
                            />
                          </div>
                        ) : (
                          // ── Normal display mode ────────────────────────────
                          <button
                            onClick={() => { onSelect(c.id); onCloseMobile?.(); }}
                            onDoubleClick={(e) => startEditing(c, e)}
                            className={cn(
                              "flex w-full items-start gap-2 rounded-xl px-3 py-2 pr-16 text-left text-sm transition-colors",
                              "hover:bg-sidebar-accent",
                              isActive && "bg-sidebar-accent border-l-[3px] border-primary pl-[9px]",
                            )}
                          >
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-medium text-sidebar-foreground" title={c.title}>
                                {formatChatTitle(c.title)}
                              </p>
                              <span className="text-xs text-muted-foreground">
                                {relTime(c.updatedAt)}
                              </span>
                            </div>
                          </button>
                        )}

                        {!isEditing && (
                          <>
                            {/* Pencil rename icon */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={(e) => startEditing(c, e)}
                              className="absolute right-8 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground hover:bg-background opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                              aria-label="Rename chat"
                              title="Rename chat"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            {/* Delete icon */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                              className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground hover:bg-background hover:text-destructive focus-visible:text-destructive md:opacity-80 md:group-hover:opacity-100 md:group-focus-within:opacity-100"
                              aria-label="Delete chat"
                              title="Delete chat"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </>
                        )}
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
