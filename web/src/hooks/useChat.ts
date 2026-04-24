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
  markMessageEdited,
  PLAN_QUOTAS,
  renameConversation,
  truncateAfterMessage,
} from "@/lib/chat";
import { useAuth } from "./useAuth";
import { ApiService } from "@/services/api";
import type { ChatStreamRequest } from "@/components/chat/ChatStream";

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
  const [streamConversationId, setStreamConversationId] = useState<string | null>(null);
  const [isResponding, setIsResponding] = useState(false);
  /** Cumulative word count for the active conversation (tracked client-side too). */
  const [sessionWordCount, setSessionWordCount] = useState(0);

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

  // Reset session word count when active conversation changes
  useEffect(() => {
    setSessionWordCount(0);
  }, [activeId]);

  const quota = PLAN_QUOTAS[user?.plan ?? "free"];
  const remaining = quota === Infinity ? Infinity : Math.max(0, quota - usage);
  const limitReached = remaining === 0;
  const active = conversations.find((c) => c.id === activeId) ?? null;

  const newChat = useCallback(() => {
    if (!phone) return null;
    const c = createConversation(phone);
    setConversations(loadConversations(phone));
    setActiveId(c.id);
    setSessionWordCount(0);
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

  const renameChat = useCallback(
    async (id: string, newTitle: string) => {
      if (!phone) return;
      const conv = conversations.find((c) => c.id === id);
      const prevTitle = conv?.title ?? "";
      // Optimistic update
      renameConversation(phone, id, newTitle);
      setConversations(loadConversations(phone));
      try {
        await ApiService.updateConversationTitle(id, phone, newTitle);
      } catch {
        // Revert on failure
        renameConversation(phone, id, prevTitle);
        setConversations(loadConversations(phone));
      }
    },
    [phone, conversations],
  );

  const send = useCallback(
    async (text: string, imageUrl?: string) => {
      if (!phone || !text.trim() || isResponding) return;
      if (limitReached) return;

      let convId = activeId;
      if (!convId) {
        const c = createConversation(phone);
        convId = c.id;
        setActiveId(c.id);
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
      setConversations(loadConversations(phone));

      const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
      setSessionWordCount((prev) => prev + wordCount);

      setIsResponding(true);
      setStreamConversationId(convId);
      setStreamRequest({
        query: text.trim(),
        imageBase64: imageUrl,
        board: user?.board || "cbse",
        classLevel: user?.classNum || 10,
        subject: active?.subject || "",
        language: user?.languages?.[0] || "en",
        conversationId: convId,
      });
    },
    [phone, activeId, isResponding, limitReached, user, active?.subject],
  );

  /** Called when edit-mode resubmits a user message (branch from here). */
  const sendEdit = useCallback(
    (convId: string, messageId: string, newContent: string, originalContent: string) => {
      if (!phone || isResponding) return;

      // Optimistic: mark edited and trim downstream messages
      markMessageEdited(phone, convId, messageId, newContent, originalContent);
      truncateAfterMessage(phone, convId, messageId);
      setConversations(loadConversations(phone));

      setIsResponding(true);
      setStreamConversationId(convId);
      setStreamRequest({
        query: newContent,
        board: user?.board || "cbse",
        classLevel: user?.classNum || 10,
        subject: active?.subject || "",
        language: user?.languages?.[0] || "en",
        conversationId: convId,
        editMessageId: messageId,
      });
    },
    [phone, isResponding, user, active?.subject],
  );

  const onStreamComplete = useCallback(
    (msg: ChatMessage) => {
      const convId = streamConversationId || activeId;
      if (!phone || !convId) return;
      appendMessage(phone, convId, msg);
      setConversations(loadConversations(phone));
      setStreamRequest(null);
      setStreamConversationId(null);
      setIsResponding(false);
    },
    [phone, activeId, streamConversationId],
  );

  const onStreamError = useCallback((err: Error) => {
    console.error("Stream Error", err);
    setIsResponding(false);
  }, []);

  return {
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
    setStreamRequest,
    isResponding,
    usage,
    quota,
    remaining,
    limitReached,
    sessionWordCount,
  };
}
