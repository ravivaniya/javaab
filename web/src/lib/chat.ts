/**
 * Chat store — conversations persisted in localStorage.
 * Namespaced under a fixed "widget" key (no per-student identity).
 */

export type Confidence = "verified" | "ai" | "low";
export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  confidence?: Confidence;
  source?: { book: string; chapter: string };
  modelName?: string;
  rawAnswer?: string;
  imageUrl?: string;
  is_edited?: boolean;
  original_text?: string;
  bookmarked?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  subject?: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  saved?: boolean;
}

const STORE_KEY = "javaab.widget.chat";
export const CHAT_TITLE_MAX_LENGTH = 25;

/** Load all conversations (newest first). */
export function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    const arr: Conversation[] = raw ? JSON.parse(raw) : [];
    return arr.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

function persist(list: Conversation[]) {
  localStorage.setItem(STORE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("javaab:chat"));
}

export function createConversation(subject?: string): Conversation {
  const conv: Conversation = {
    id: crypto.randomUUID(),
    title: "New chat",
    subject,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
  const list = loadConversations();
  list.unshift(conv);
  persist(list);
  return conv;
}

export function deleteConversation(id: string) {
  persist(loadConversations().filter((c) => c.id !== id));
}

export function renameConversation(id: string, title: string) {
  const list = loadConversations();
  const idx = list.findIndex((c) => c.id === id);
  if (idx === -1) return;
  list[idx].title = title.trim().slice(0, CHAT_TITLE_MAX_LENGTH) || "New chat";
  list[idx].updatedAt = Date.now();
  persist(list);
}

export function formatChatTitle(title: string): string {
  const cleanTitle = title.trim() || "New chat";
  if (cleanTitle.length <= CHAT_TITLE_MAX_LENGTH) return cleanTitle;
  return `${cleanTitle.slice(0, CHAT_TITLE_MAX_LENGTH).trimEnd()}...`;
}

export function appendMessage(convId: string, msg: ChatMessage) {
  const list = loadConversations();
  const idx = list.findIndex((c) => c.id === convId);
  if (idx === -1) return;
  const conv = list[idx];
  conv.messages.push(msg);
  conv.updatedAt = Date.now();
  if (msg.role === "user" && conv.title === "New chat") {
    conv.title = formatChatTitle(msg.content);
  }
  list[idx] = conv;
  persist(list);
}

export function truncateAfterMessage(convId: string, messageId: string) {
  const list = loadConversations();
  const idx = list.findIndex((c) => c.id === convId);
  if (idx === -1) return;
  const conv = list[idx];
  const msgIdx = conv.messages.findIndex((m) => m.id === messageId);
  if (msgIdx === -1) return;
  conv.messages = conv.messages.slice(0, msgIdx + 1);
  conv.updatedAt = Date.now();
  list[idx] = conv;
  persist(list);
}

export function markMessageEdited(
  convId: string,
  messageId: string,
  newContent: string,
  originalText: string,
) {
  const list = loadConversations();
  const conv = list.find((c) => c.id === convId);
  if (!conv) return;
  const msg = conv.messages.find((m) => m.id === messageId);
  if (!msg) return;
  msg.original_text = originalText;
  msg.content = newContent;
  msg.is_edited = true;
  conv.updatedAt = Date.now();
  persist(list);
}

export function bookmarkMessage(convId: string, messageId: string): boolean {
  const list = loadConversations();
  const conv = list.find((c) => c.id === convId);
  if (!conv) return false;
  const msg = conv.messages.find((m) => m.id === messageId);
  if (!msg) return false;
  msg.bookmarked = !msg.bookmarked;
  conv.saved = conv.messages.some((m) => m.bookmarked);
  persist(list);
  return msg.bookmarked;
}

export type DateBucket = "Today" | "Yesterday" | "This Week" | "Earlier";
export function bucketOf(ts: number): DateBucket {
  const now = new Date();
  const then = new Date(ts);
  const diffDays = Math.floor(
    (+startOfDay(now) - +startOfDay(then)) / 86400000,
  );
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "This Week";
  return "Earlier";
}
function startOfDay(d: Date) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}
