import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  BookOpen,
  Check,
  ChevronDown,
  Copy,
  Pencil,
  Sparkles,
  ShieldCheck,
  X,
} from "lucide-react";
import { ChatMessage } from "@/lib/chat";
import { Markdown } from "./Markdown";
import { TypingDots } from "./TypingDots";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface Props {
  message: ChatMessage;
  /** Called when the user submits an edit (branch-from-here). */
  onEdit?: (
    messageId: string,
    newContent: string,
    originalContent: string,
  ) => void;
  /** Called when the user bookmarks an assistant message. */
  onBookmark?: (messageId: string) => void;
}

const CONFIDENCE_META = {
  verified: {
    label: "Verified ✅",
    Icon: ShieldCheck,
    className: "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]",
  },
  ai: {
    label: "AI Generated",
    Icon: Sparkles,
    className: "bg-accent text-accent-foreground",
  },
  low: {
    label: "Low Confidence",
    Icon: AlertTriangle,
    className: "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))]",
  },
} as const;

/** Collapse AI responses taller than this px threshold. */
const COLLAPSE_THRESHOLD = 420;

// ─────────────────────────────────────────────────────────────────────────────
// User message bubble
// ─────────────────────────────────────────────────────────────────────────────

function UserBubble({
  message,
  onEdit,
}: {
  message: ChatMessage;
  onEdit?: Props["onEdit"];
}) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(message.content);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleCopy() {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  function handleEditStart() {
    if (message.is_edited) return;
    setEditValue(message.content);
    setIsEditing(true);
    setTimeout(() => {
      textareaRef.current?.focus();
      textareaRef.current?.select();
    }, 0);
  }

  function handleEditSubmit() {
    const trimmed = editValue.trim();
    if (!trimmed || trimmed === message.content) {
      setIsEditing(false);
      return;
    }
    onEdit?.(message.id, trimmed, message.content);
    setIsEditing(false);
  }

  return (
    <div className="flex w-full justify-end">
      <div className="group relative max-w-[85%] space-y-2 sm:max-w-[75%]">
        <div className="rounded-3xl rounded-tr-md bg-primary/10 px-5 py-3 text-foreground break-words overflow-wrap-anywhere">
          {message.imageUrl && (
            <>
              <img
                src={message.imageUrl}
                alt="Attached"
                className="mb-2 h-20 w-20 cursor-pointer rounded-xl object-cover"
                onClick={() => setLightboxOpen(true)}
                title="Click to view full image"
              />
              {/* TODO: For production, store in Azure Blob Storage and save only the blob URL */}
            </>
          )}
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                ref={textareaRef}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleEditSubmit();
                  }
                  if (e.key === "Escape") setIsEditing(false);
                }}
                className="w-full resize-none rounded-lg bg-background/60 p-2 text-[15px] leading-relaxed outline-none ring-1 ring-primary/30 focus:ring-primary min-h-[60px]"
                rows={3}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="rounded-pill"
                  onClick={handleEditSubmit}
                >
                  Send
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="rounded-pill"
                  onClick={() => setIsEditing(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed text-[15px] break-words">
              {message.content}
            </p>
          )}

          {message.is_edited && (
            <div className="relative inline-block">
              <span
                className="mt-1 inline-block cursor-help text-[11px] text-muted-foreground underline decoration-dotted"
                title={
                  message.original_text
                    ? `Original: ${message.original_text}`
                    : "Message was edited"
                }
              >
                (edited)
              </span>
            </div>
          )}
        </div>

        {/* Hover action row */}
        {!isEditing && (
          <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
              title="Copy message"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-6 w-6",
                message.is_edited
                  ? "cursor-not-allowed text-muted-foreground/40"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={handleEditStart}
              disabled={message.is_edited}
              title={message.is_edited ? "Already edited" : "Edit message"}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightboxOpen && message.imageUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setLightboxOpen(false)}
        >
          <img
            src={message.imageUrl}
            alt="Full size"
            className="max-h-[90vh] max-w-[90vw] rounded-xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
            onClick={() => setLightboxOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Assistant message bubble
// ─────────────────────────────────────────────────────────────────────────────

function AssistantBubble({
  message,
  onBookmark,
}: {
  message: ChatMessage;
  onBookmark?: Props["onBookmark"];
}) {
  const [showSource, setShowSource] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(message.bookmarked ?? false);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [needsCollapse, setNeedsCollapse] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const meta = CONFIDENCE_META[message.confidence ?? "ai"];
  const hasContent = message.content.trim().length > 0;

  // Sync bookmark state if parent updates message prop (e.g. cross-tab)
  useEffect(() => {
    setIsBookmarked(message.bookmarked ?? false);
  }, [message.bookmarked]);

  // Measure rendered height to decide whether to collapse
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    if (el.scrollHeight > COLLAPSE_THRESHOLD) {
      setNeedsCollapse(true);
    }
  }, [message.content]);

  function handleCopy() {
    const text = message.rawAnswer ?? message.content;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  function handleBookmark() {
    const next = !isBookmarked;
    setIsBookmarked(next);
    onBookmark?.(message.id);
  }

  return (
    <div className="flex w-full justify-start">
      <div className="group relative max-w-[92%] space-y-3 rounded-3xl rounded-tl-md bg-card px-5 py-4 shadow-sm ring-1 ring-border/50 sm:max-w-[80%] break-words overflow-wrap-anywhere">
        {!hasContent ? (
          <TypingDots />
        ) : (
          <>
            {/* Collapsible content area */}
            <div className="relative">
              <div
                ref={contentRef}
                className={cn(
                  "overflow-hidden",
                  needsCollapse && !isExpanded && "max-h-[420px]",
                )}
              >
                <Markdown>{message.content}</Markdown>
              </div>

              {/* Fade gradient when collapsed */}
              {needsCollapse && !isExpanded && (
                <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-card to-transparent" />
              )}
            </div>

            {/* Show more / Show less */}
            {needsCollapse && (
              <button
                onClick={() => setIsExpanded((v) => !v)}
                className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                {isExpanded ? (
                  <>
                    <ChevronDown className="h-4 w-4 rotate-180" /> Show less ↑
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4" /> Show more ↓
                  </>
                )}
              </button>
            )}

            {/* Source + confidence + bookmark + copy row */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {message.source && (
                <button
                  onClick={() => setShowSource((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/70"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  Source
                  <ChevronDown
                    className={cn(
                      "h-3.5 w-3.5 transition-transform",
                      showSource && "rotate-180",
                    )}
                  />
                </button>
              )}

              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                  meta.className,
                )}
              >
                <meta.Icon className="h-3.5 w-3.5" />
                {meta.label}
              </span>

              <div className="ml-auto flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-7 w-7 transition-all",
                    isBookmarked && "text-primary scale-110",
                  )}
                  onClick={handleBookmark}
                  aria-label={
                    isBookmarked
                      ? "Remove bookmark"
                      : "Save for quick reference"
                  }
                  title={
                    isBookmarked
                      ? "Remove bookmark"
                      : "Save for quick reference"
                  }
                >
                  {isBookmarked ? (
                    <BookmarkCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Bookmark className="h-3.5 w-3.5" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleCopy}
                  aria-label="Copy answer"
                  title="Copy answer"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              </div>
            </div>

            {showSource && message.source && (
              <div className="rounded-2xl border border-dashed border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground animate-fade-in">
                <p className="font-semibold text-foreground">
                  {message.source.book}
                </p>
                <p>{message.source.chapter}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────────────────────────────

export function MessageBubble({ message, onEdit, onBookmark }: Props) {
  if (message.role === "user") {
    return <UserBubble message={message} onEdit={onEdit} />;
  }
  return <AssistantBubble message={message} onBookmark={onBookmark} />;
}
