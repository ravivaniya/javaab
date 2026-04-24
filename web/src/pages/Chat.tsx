import { useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { AppHeader } from "@/components/AppHeader";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { QuickStartChips } from "@/components/chat/QuickStartChips";
import { ChatInput } from "@/components/chat/ChatInput";
import { RateLimitCard } from "@/components/chat/RateLimitCard";
import { ChatStream } from "@/components/chat/ChatStream";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";

/** Main chat surface — header + sidebar + thread + input. */
export default function Chat() {
  const { user } = useAuth();
  const {
    conversations,
    active,
    activeId,
    setActiveId,
    newChat,
    removeChat,
    renameChat,
    send,
    sendEdit,
    streamRequest,
    onStreamComplete,
    onStreamError,
    isResponding,
    remaining,
    quota,
    usage,
    sessionWordCount,
  } = useChat();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPaid = user?.plan === "plus" || user?.plan === "pro";
  const isPro = user?.plan === "pro";
  const limitReached = remaining === 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, isResponding]);

  const counterLabel = isPro ? "∞" : `${Math.max(0, quota - usage)} left`;
  const questionCounter = (
    <span
      className={`rounded-full px-3 py-1 text-[11px] font-semibold ${
        limitReached
          ? "bg-destructive/10 text-destructive"
          : "bg-muted text-muted-foreground"
      }`}
    >
      {counterLabel}
    </span>
  );

  const Sidebar = (mobile = false) => (
    <ChatSidebar
      conversations={conversations}
      activeId={activeId}
      onSelect={setActiveId}
      onNew={newChat}
      onDelete={removeChat}
      onRename={renameChat}
      onCloseMobile={() => setMobileOpen(false)}
      collapsed={!mobile && collapsed}
      onToggleCollapse={mobile ? undefined : () => setCollapsed((c) => !c)}
    />
  );

  const mobileTrigger = (
    <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open chat history"
        >
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px] p-0">
        {Sidebar(true)}
      </SheetContent>
    </Sheet>
  );

  return (
    <div className="flex h-screen w-full flex-col bg-background">
      <AppHeader leftSlot={mobileTrigger} rightSlot={questionCounter} />

      <div className="flex min-h-0 flex-1">
        {/* Desktop sidebar */}
        <div
          className={`hidden h-full shrink-0 border-r border-border transition-[width] duration-200 md:block ${
            collapsed ? "w-[60px]" : "w-[280px]"
          }`}
        >
          {Sidebar()}
        </div>

        {/* Main */}
        <div className="flex h-full min-w-0 flex-1 flex-col">
          {/* Thread */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            {!active || active.messages.length === 0 ? (
              <QuickStartChips
                name={user?.name}
                classNum={user?.classNum}
                board={user?.board}
                onPick={(t) => {
                  if (!limitReached) send(t);
                }}
              />
            ) : (
              <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6 sm:px-6">
                {active.messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    onEdit={
                      m.role === "user" && activeId
                        ? (msgId, newContent, originalContent) =>
                            sendEdit(
                              activeId,
                              msgId,
                              newContent,
                              originalContent,
                            )
                        : undefined
                    }
                  />
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
              sessionWordCount={sessionWordCount}
              onNewChat={newChat}
            />
            <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
              Javaab can make mistakes. Verify important answers with your
              textbook.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
