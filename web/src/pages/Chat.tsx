import { useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { QuickStartChips } from "@/components/chat/QuickStartChips";
import { ChatInput } from "@/components/chat/ChatInput";
import { RateLimitCard } from "@/components/chat/RateLimitCard";
import { ChatStream } from "@/components/chat/ChatStream";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

/** Main chat surface — sidebar + thread + input. */
export default function Chat() {
  const { user } = useAuth();
  const {
    conversations,
    active,
    activeId,
    setActiveId,
    newChat,
    removeChat,
    send,
    streamRequest,
    onStreamComplete,
    onStreamError,
    isResponding,
    remaining,
    quota,
    usage,
  } = useChat();

  const [mobileOpen, setMobileOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPaid = user?.plan === "plus" || user?.plan === "pro";
  const isPro = user?.plan === "pro";
  const limitReached = remaining === 0;

  // Auto-scroll to bottom on new content
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, isResponding]);

  const subjectChip =
    user?.board && user?.classNum
      ? `Class ${user.classNum} · ${user.board.toUpperCase()}`
      : "Choose subject";

  const counterLabel = isPro ? "∞" : `${Math.max(0, quota - usage)} left`;

  const Sidebar = (
    <ChatSidebar
      conversations={conversations}
      activeId={activeId}
      onSelect={setActiveId}
      onNew={newChat}
      onDelete={removeChat}
      onCloseMobile={() => setMobileOpen(false)}
    />
  );

  return (
    <div className="flex h-screen w-full bg-background">
      {/* Desktop sidebar */}
      <div className="hidden h-full w-[260px] shrink-0 border-r border-border md:block">
        {Sidebar}
      </div>

      {/* Main */}
      <div className="flex h-full min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-card/60 px-3 backdrop-blur sm:px-5">
          <div className="flex items-center gap-2">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="md:hidden"
                  aria-label="Open menu"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-[280px] p-0">
                {Sidebar}
              </SheetContent>
            </Sheet>
          </div>

          <button
            type="button"
            className="rounded-pill bg-accent px-4 py-1.5 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/80"
            onClick={() => (window.location.href = "/subjects")}
          >
            {subjectChip}
          </button>

          <div className="flex items-center gap-3">
            <span
              className={`hidden rounded-full px-3 py-1 text-xs font-semibold sm:inline-block ${
                limitReached
                  ? "bg-destructive/10 text-destructive"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {counterLabel}
            </span>
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                {user?.phone?.slice(-2) ?? "JV"}
              </AvatarFallback>
            </Avatar>
          </div>
        </header>

        {/* Thread */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {!active || active.messages.length === 0 ? (
            <QuickStartChips
              name={user?.name}
              onPick={(t) => {
                if (!limitReached) send(t);
              }}
            />
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
              {active.messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {streamRequest && (
                <ChatStream
                  request={streamRequest}
                  userId={user?.phone ?? ""}
                  plan={user?.plan ?? "free"}
                  usageCount={usage}
                  onComplete={onStreamComplete}
                  onError={onStreamError}
                />
              )}
              {limitReached && !streamRequest && (
                <RateLimitCard used={quota} plan={user?.plan ?? "free"} />
              )}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-border bg-background/80 px-3 py-3 backdrop-blur sm:px-6 sm:py-4">
          <ChatInput
            onSend={send}
            disabled={isResponding || limitReached}
            isPaid={isPaid}
          />
          <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
            Javaab can make mistakes. Verify important answers with your textbook.
          </p>
        </div>
      </div>
    </div>
  );
}
