import { useCallback, useEffect, useState } from "react";
import {
  appendMessage,
  bookmarkMessage,
  ChatMessage,
  Conversation,
  createConversation,
  deleteConversation,
  loadConversations,
  markMessageEdited,
  renameConversation,
  truncateAfterMessage,
} from "@/lib/chat";
import { ApiService } from "@/services/api";
import { widgetConfig } from "@/config/widget.config";
import type { ChatStreamRequest } from "@/components/chat/ChatStream";

/** Reactive chat state for the widget (no per-student identity). */
export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    loadConversations(),
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streamRequest, setStreamRequest] = useState<ChatStreamRequest | null>(null);
  const [streamConversationId, setStreamConversationId] = useState<string | null>(null);
  const [isResponding, setIsResponding] = useState(false);

  const reload = () => setConversations(loadConversations());

  useEffect(() => {
    const sync = () => reload();
    window.addEventListener("javaab:chat", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("javaab:chat", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const active = conversations.find((c) => c.id === activeId) ?? null;

  const newChat = useCallback(() => {
    const c = createConversation();
    reload();
    setActiveId(c.id);
    return c;
  }, []);

  const removeChat = useCallback(
    (id: string) => {
      deleteConversation(id);
      reload();
      if (activeId === id) setActiveId(null);
    },
    [activeId],
  );

  const renameChat = useCallback(
    async (id: string, newTitle: string) => {
      const conv = conversations.find((c) => c.id === id);
      const prevTitle = conv?.title ?? "";
      renameConversation(id, newTitle);
      reload();
      try {
        await ApiService.updateConversationTitle(id, newTitle);
      } catch {
        renameConversation(id, prevTitle);
        reload();
      }
    },
    [conversations],
  );

  const send = useCallback(
    async (text: string, imageUrl?: string) => {
      if (!text.trim() || isResponding) return;

      let convId = activeId;
      if (!convId) {
        const c = createConversation();
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
      appendMessage(convId, userMsg);
      reload();

      setIsResponding(true);
      setStreamConversationId(convId);
      setStreamRequest({
        query: text.trim(),
        imageBase64: imageUrl,
        board: widgetConfig.defaults.board,
        classLevel: widgetConfig.defaults.class_level,
        subject: active?.subject || "",
        language: widgetConfig.defaults.language,
        conversationId: convId,
      });
    },
    [activeId, isResponding, active?.subject],
  );

  const sendEdit = useCallback(
    (convId: string, messageId: string, newContent: string, originalContent: string) => {
      if (isResponding) return;
      markMessageEdited(convId, messageId, newContent, originalContent);
      truncateAfterMessage(convId, messageId);
      reload();
      setIsResponding(true);
      setStreamConversationId(convId);
      setStreamRequest({
        query: newContent,
        board: widgetConfig.defaults.board,
        classLevel: widgetConfig.defaults.class_level,
        subject: active?.subject || "",
        language: widgetConfig.defaults.language,
        conversationId: convId,
        editMessageId: messageId,
      });
    },
    [isResponding, active?.subject],
  );

  const onStreamComplete = useCallback(
    (msg: ChatMessage) => {
      const convId = streamConversationId || activeId;
      if (!convId) return;
      appendMessage(convId, msg);
      reload();
      setStreamRequest(null);
      setStreamConversationId(null);
      setIsResponding(false);
    },
    [activeId, streamConversationId],
  );

  const onStreamError = useCallback(() => {
    setIsResponding(false);
  }, []);

  const bookmarkChat = useCallback(
    (convId: string, messageId: string) => {
      bookmarkMessage(convId, messageId);
      reload();
    },
    [],
  );

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
    bookmarkChat,
  };
}
