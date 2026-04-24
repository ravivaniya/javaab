export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface FetchOptions extends RequestInit {
  requiresAuth?: boolean;
}

/** Base fetch wrapper with error handling. */
async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

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
    onMetadata?: (model: string, confidence: string, fromCache: boolean, conversationId?: string) => void;
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
              callbacks.onMetadata?.(data.model, data.confidence, data.from_cache ?? false, data.conversation_id);
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

  async registerUser(data: { phone: string }) {
    return fetchApi("/auth/register", { method: "POST", body: JSON.stringify(data) });
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
      onMetadata: (model: string, confidence: string, fromCache?: boolean, conversationId?: string) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    },
  ) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
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
      const response = await fetch(
        `${API_BASE_URL}/chat/${conversationId}/message/${messageId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Edit message failed: ${response.status}`);
      }

      await consumeSseStream(response, callbacks);
    } catch (err) {
      callbacks.onError(err);
    }
  },

  // ── Chat: feedback ────────────────────────────────────────────────────────

  async sendFeedback(
    messageId: string,
    isPositive: boolean,
    dislikeReason?: string,
    fromCache?: boolean,
    confidence?: string,
  ) {
    return fetchApi("/chat/feedback", {
      method: "POST",
      body: JSON.stringify({
        message_id: messageId,
        is_positive: isPositive,
        dislike_reason: dislikeReason ?? null,
        from_cache: fromCache ?? false,
        confidence: confidence ?? null,
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
