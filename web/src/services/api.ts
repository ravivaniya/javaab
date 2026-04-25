import { getToken, clearToken, clearUser } from "@/lib/auth";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface FetchOptions extends RequestInit {
  requiresAuth?: boolean;
}

/** Endpoints that must NEVER carry an Authorization header. */
const PUBLIC_ENDPOINTS = ["/auth/login", "/auth/verify", "/auth/register", "/health"];

function isPublicEndpoint(endpoint: string): boolean {
  return PUBLIC_ENDPOINTS.some((p) => endpoint === p || endpoint.startsWith(`${p}?`));
}

/** Attach the stored JWT (if any) to a Headers object. */
function attachAuth(headers: Headers, endpoint: string): void {
  if (isPublicEndpoint(endpoint)) return;
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
}

/** Centralised 401 handler — drop the stored session so the user re-logs in. */
function handleUnauthorized(): void {
  clearToken();
  clearUser();
}

/** Base fetch wrapper with error handling. */
async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  attachAuth(headers, endpoint);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "An error occurred";
    try {
      const data = await response.json();
      message = data.detail || data.message || message;
    } catch {
      message = `Status: ${response.status}`;
    }
    if (response.status === 401) {
      handleUnauthorized();
      const err = new Error(message);
      err.name = "AuthError";
      throw err;
    }
    if (response.status === 429) {
      const err = new Error(message);
      err.name = "RateLimitError";
      throw err;
    }
    throw new Error(message);
  }

  return response.json();
}

/** Shared SSE stream reader — parses data events and fires callbacks. */
async function consumeSseStream(
  response: Response,
  callbacks: {
    onChunk?: (content: string) => void;
    onConversationId?: (id: string) => void;
    onMetadata?: (model: string, confidence: string, fromCache: boolean, conversationId?: string, confidenceScore?: number) => void;
    onSources?: (sources: Record<string, unknown>[]) => void;
    onDone?: () => void;
    onError?: (err: unknown) => void;
  },
) {
  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      if (raw.startsWith("data: ")) {
        const dataStr = raw.replace(/^data:\s*/, "");
        if (dataStr === "[DONE]") {
          callbacks.onDone?.();
        } else {
          try {
            const data = JSON.parse(dataStr);
            if (data.type === "chunk") {
              callbacks.onChunk?.(data.content);
            } else if (data.type === "conversation_id") {
              callbacks.onConversationId?.(data.id);
            } else if (data.type === "metadata") {
              callbacks.onMetadata?.(data.model, data.confidence, data.from_cache ?? false, data.conversation_id, data.confidence_score);
            } else if (data.type === "sources") {
              callbacks.onSources?.(data.sources);
            } else if (data.type === "done") {
              callbacks.onDone?.();
            }
          } catch (e) {
            console.error("Failed to parse SSE line:", raw, e);
          }
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
  callbacks.onDone?.();
}

export const ApiService = {
  // ── Auth / Profile ──────────────────────────────────────────────────────

  async registerUser(data: { phone: string; name?: string; class_level?: number; board?: string; language?: string; referral_code?: string }) {
    return fetchApi<{
      status: string;
      user_id: string;
      referral_code: string;
      access_token: string;
      token_type: string;
    }>("/auth/register", { method: "POST", body: JSON.stringify(data) });
  },

  async loginRequestOtp(phone: string) {
    return fetchApi<{ status: string; message: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ phone }),
    });
  },

  async verifyOtpRemote(phone: string, otp: string) {
    return fetchApi<{ access_token: string; token_type: string; token: string }>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ phone, otp }),
    });
  },

  async updateProfile(data: Record<string, unknown>) {
    return fetchApi("/student/profile", { method: "POST", body: JSON.stringify(data) });
  },

  // ── Subjects ─────────────────────────────────────────────────────────────

  async getSubjects(board: string, classLevel: number) {
    return fetchApi(`/subjects/${board}/${classLevel}`);
  },

  // ── Chat: ask (SSE stream) ────────────────────────────────────────────────

  async askChatStream(
    body: {
      query: string;
      user_id: string;
      image_base64?: string;
      board: string;
      class_level: number;
      subject?: string;
      language: string;
      conversation_id?: string;
      retry_of?: string;
    },
    callbacks: {
      onChunk: (content: string) => void;
      onConversationId?: (id: string) => void;
      onMetadata: (model: string, confidence: string, fromCache?: boolean, conversationId?: string, confidenceScore?: number) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    },
  ) {
    try {
      const headers = new Headers({ "Content-Type": "application/json" });
      attachAuth(headers, "/chat/ask");
      const response = await fetch(`${API_BASE_URL}/chat/ask`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        if (response.status === 401) {
          handleUnauthorized();
          const err = new Error("Session expired. Please sign in again.");
          err.name = "AuthError";
          throw err;
        }
        if (response.status === 429 || response.status === 503) {
          const data = await response.json().catch(() => ({}));
          const err = new Error(data.detail?.message || data.detail || "Request limit reached");
          err.name = response.status === 429 ? "RateLimitError" : "CapacityError";
          throw err;
        }
        throw new Error(`Chat API failed: ${response.status}`);
      }

      await consumeSseStream(response, callbacks);
    } catch (err) {
      callbacks.onError(err);
    }
  },

  // ── Chat: edit message (SSE stream) ──────────────────────────────────────

  async editMessageStream(
    conversationId: string,
    messageId: string,
    body: { user_id: string; content: string },
    callbacks: {
      onChunk: (content: string) => void;
      onMetadata: (model: string, confidence: string, fromCache?: boolean) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    },
  ) {
    try {
      const headers = new Headers({ "Content-Type": "application/json" });
      attachAuth(headers, `/chat/${conversationId}/message/${messageId}`);
      const response = await fetch(
        `${API_BASE_URL}/chat/${conversationId}/message/${messageId}`,
        {
          method: "PATCH",
          headers,
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        if (response.status === 401) {
          handleUnauthorized();
          const err = new Error("Session expired. Please sign in again.");
          err.name = "AuthError";
          throw err;
        }
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Edit message failed: ${response.status}`);
      }

      await consumeSseStream(response, callbacks);
    } catch (err) {
      callbacks.onError(err);
    }
  },

  // ── Chat: bookmark message ────────────────────────────────────────────────

  async bookmarkMessage(messageId: string, conversationId: string, userId: string, content?: string) {
    return fetchApi("/chat/bookmark", {
      method: "POST",
      body: JSON.stringify({
        message_id: messageId,
        conversation_id: conversationId,
        user_id: userId,
        content: content ?? null,
      }),
    });
  },

  // ── Chat: rename conversation ─────────────────────────────────────────────

  async updateConversationTitle(conversationId: string, userId: string, title: string) {
    return fetchApi(`/chat/${conversationId}/title`, {
      method: "PATCH",
      body: JSON.stringify({ user_id: userId, title }),
    });
  },

  // ── Util: client-side image compression ──────────────────────────────────

  async compressImageToBase64(file: File, maxWidth = 1000, maxHeight = 1000): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let { width, height } = img;

          if (width > height) {
            if (width > maxWidth) { height = Math.round((height * maxWidth) / width); width = maxWidth; }
          } else {
            if (height > maxHeight) { width = Math.round((width * maxHeight) / height); height = maxHeight; }
          }

          const canvas = document.createElement("canvas");
          canvas.width = width;
          canvas.height = height;

          const ctx = canvas.getContext("2d");
          if (!ctx) return reject("Canvas ctx null");
          ctx.drawImage(img, 0, 0, width, height);

          const dataUrl = canvas.toDataURL(file.type, 0.85);
          resolve(dataUrl.split(",")[1]);
        };
        img.onerror = reject;
        img.src = e.target?.result as string;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  },
};
