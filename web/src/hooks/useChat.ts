import { useCallback, useEffect, useState } from "react";
import {
  appendMessage,
  bumpUsage,
  ChatMessage,
  Conversation,
  createConversation,
  deleteConversation,
  getUsage,
  loadConversations,
  updateMessage,
  PLAN_QUOTAS,
  type Confidence,
} from "@/lib/chat";
import { useAuth } from "./useAuth";
import { ChatStreamRequest } from "@/components/chat/ChatStream";

/** Reactive chat state for the current authed user. */
export function useChat() {
  const { user } = useAuth();
  const phone = user?.phone ?? "";
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    phone ? loadConversations(phone) : [],
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [usage, setUsage] = useState<number>(() => (phone ? getUsage(phone) : 0));
  const [streamRequest, setStreamRequest] = useState<ChatStreamRequest | null>(null);
  const [isResponding, setIsResponding] = useState(false);

  // Sync from storage on cross-tab edits
  useEffect(() => {
    if (!phone) return;
    const sync = () => {
      setConversations(loadConversations(phone));
      setUsage(getUsage(phone));
    };
    window.addEventListener("javaab:chat", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("javaab:chat", sync);
      window.removeEventListener("storage", sync);
    };
  }, [phone]);

  const quota = PLAN_QUOTAS[user?.plan ?? "free"];
  const remaining = quota === Infinity ? Infinity : Math.max(0, quota - usage);
  const limitReached = remaining === 0;

  const newChat = useCallback(() => {
    if (!phone) return null;
    const c = createConversation(phone);
    setConversations(loadConversations(phone));
    setActiveId(c.id);
    return c;
  }, [phone]);

  const removeChat = useCallback(
    (id: string) => {
      if (!phone) return;
      deleteConversation(phone, id);
      setConversations(loadConversations(phone));
      if (activeId === id) setActiveId(null);
    },
    [phone, activeId],
  );

  const active = conversations.find((c) => c.id === activeId) ?? null;

  const send = useCallback(
    async (text: string, imageUrl?: string) => {
      if (!phone || !text.trim() || isResponding) return;
      if (limitReached) return;

      // Ensure we have an active conversation
      let convId = activeId;
      let isFirstReply = false;
      if (!convId) {
        const c = createConversation(phone);
        convId = c.id;
        setActiveId(c.id);
        isFirstReply = true;
      } else {
        const cur = conversations.find((c) => c.id === convId);
        isFirstReply = !cur || cur.messages.length === 0;
      }

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        createdAt: Date.now(),
        imageUrl,
      };
      appendMessage(phone, convId, userMsg);
      const newUsage = bumpUsage(phone);
      setUsage(newUsage);
      setIsResponding(true);
      setConversations(loadConversations(phone));

      setStreamRequest({
        query: text.trim(),
        imageBase64: imageUrl,
        board: user?.board || "cbse",
        classLevel: user?.classNum || 10,
        subject: active?.subject || "general",
        language: user?.languages?.[0] || "en",
      });
    },
    [phone, activeId, conversations, isResponding, limitReached, user, active?.subject],
  );

  const onStreamComplete = useCallback(
    (msg: ChatMessage) => {
      if (!phone || !activeId) return;
      appendMessage(phone, activeId, msg);
      setConversations(loadConversations(phone));
      setStreamRequest(null);
      setIsResponding(false);
    },
    [phone, activeId]
  );

  const onStreamError = useCallback((err: Error) => {
    console.error("Stream Error", err);
    // Ideally we can inject an error message bubble if we want, or rely on ChatStream showing retry.
    setIsResponding(false);
    setStreamRequest(null);
  }, []);

  return {
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
    setStreamRequest,
    isResponding,
    usage,
    quota,
    remaining,
    limitReached,
  };
}
