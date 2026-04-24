/**
 * Chat store — conversations + messages persisted in localStorage.
 * Each user (by phone) gets a namespaced store. Replace with Cloud sync later.
 */

export type Confidence = "verified" | "ai" | "low";
export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  confidence?: Confidence; // assistant only
  source?: { book: string; chapter: string }; // assistant only
  modelName?: string; // assistant only
  rawAnswer?: string; // assistant only — clean markdown for copy (no follow-up lines)
  imageUrl?: string; // user uploads (Plus/Pro)
  // Edit tracking (one-time edit allowed per user message)
  is_edited?: boolean;
  original_text?: string;
}

export interface Conversation {
  id: string;
  title: string; // first user question, up to CHAT_TITLE_MAX_LENGTH chars
  subject?: string; // e.g. "Science", "Mathematics"
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}

const PREFIX = "javaab.chat.";
const QUOTA_PREFIX = "javaab.quota.";
export const CHAT_TITLE_MAX_LENGTH = 25;

/** Plan-based monthly query quotas. */
export const PLAN_QUOTAS: Record<string, number> = {
  free: 50,
  plus: 1000,
  pro: Infinity,
};

function key(phone: string) {
  return `${PREFIX}${phone}`;
}
function quotaKey(phone: string) {
  const d = new Date();
  const m = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  return `${QUOTA_PREFIX}${phone}.${m}`;
}

/** Load all conversations for a phone (newest first). */
export function loadConversations(phone: string): Conversation[] {
  try {
    const raw = localStorage.getItem(key(phone));
    const arr: Conversation[] = raw ? JSON.parse(raw) : [];
    return arr.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

function persist(phone: string, list: Conversation[]) {
  localStorage.setItem(key(phone), JSON.stringify(list));
  window.dispatchEvent(new Event("javaab:chat"));
}

export function createConversation(
  phone: string,
  subject?: string,
): Conversation {
  const conv: Conversation = {
    id: crypto.randomUUID(),
    title: "New chat",
    subject,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
  const list = loadConversations(phone);
  list.unshift(conv);
  persist(phone, list);
  return conv;
}

export function deleteConversation(phone: string, id: string) {
  const list = loadConversations(phone).filter((c) => c.id !== id);
  persist(phone, list);
}

/** Rename a conversation locally (optimistic update). */
export function renameConversation(phone: string, id: string, title: string) {
  const list = loadConversations(phone);
  const idx = list.findIndex((c) => c.id === id);
  if (idx === -1) return;
  list[idx].title = title.trim().slice(0, CHAT_TITLE_MAX_LENGTH) || "New chat";
  list[idx].updatedAt = Date.now();
  persist(phone, list);
}

export function formatChatTitle(title: string): string {
  const cleanTitle = title.trim() || "New chat";
  if (cleanTitle.length <= CHAT_TITLE_MAX_LENGTH) return cleanTitle;
  return `${cleanTitle.slice(0, CHAT_TITLE_MAX_LENGTH).trimEnd()}...`;
}

export function appendMessage(phone: string, convId: string, msg: ChatMessage) {
  const list = loadConversations(phone);
  const idx = list.findIndex((c) => c.id === convId);
  if (idx === -1) return;
  const conv = list[idx];
  conv.messages.push(msg);
  conv.updatedAt = Date.now();
  if (msg.role === "user" && conv.title === "New chat") {
    conv.title = formatChatTitle(msg.content);
  }
  list[idx] = conv;
  persist(phone, list);
}

/**
 * Remove all messages after (not including) the given message id.
 * Used for the one-time edit "branch from here" flow.
 */
export function truncateAfterMessage(
  phone: string,
  convId: string,
  messageId: string,
) {
  const list = loadConversations(phone);
  const idx = list.findIndex((c) => c.id === convId);
  if (idx === -1) return;
  const conv = list[idx];
  const msgIdx = conv.messages.findIndex((m) => m.id === messageId);
  if (msgIdx === -1) return;
  conv.messages = conv.messages.slice(0, msgIdx + 1);
  conv.updatedAt = Date.now();
  list[idx] = conv;
  persist(phone, list);
}

/** Mark a message as edited and store the original text. */
export function markMessageEdited(
  phone: string,
  convId: string,
  messageId: string,
  newContent: string,
  originalText: string,
) {
  const list = loadConversations(phone);
  const conv = list.find((c) => c.id === convId);
  if (!conv) return;
  const msg = conv.messages.find((m) => m.id === messageId);
  if (!msg) return;
  msg.original_text = originalText;
  msg.content = newContent;
  msg.is_edited = true;
  conv.updatedAt = Date.now();
  persist(phone, list);
}

/** Quota helpers — counts user-side messages this calendar month. */
export function getUsage(phone: string): number {
  const v = localStorage.getItem(quotaKey(phone));
  return v ? Number(v) : 0;
}
export function bumpUsage(phone: string): number {
  const next = getUsage(phone) + 1;
  localStorage.setItem(quotaKey(phone), String(next));
  return next;
}

/** Date-group helper for the sidebar. */
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
