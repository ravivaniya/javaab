import { widgetConfig } from "@/config/widget.config";
import type { PaperConfig, GeneratedPaper } from "@/types/paper";
import type { WorksheetConfig, GeneratedWorksheet } from "@/types/worksheet";

// Force HTTPS in production to prevent mixed-content blocks
const rawApiUrl = widgetConfig.apiBaseUrl;
export const API_BASE_URL =
  location.protocol === "https:" && rawApiUrl.startsWith("http:")
    ? rawApiUrl.replace("http://", "https://")
    : rawApiUrl;

/** Attach the client's API key to every outgoing request. */
function attachApiKey(headers: Headers): void {
  const key = widgetConfig.apiKey;
  if (key) headers.set("X-API-Key", key);
}

/** Base fetch wrapper with error handling. */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  attachApiKey(headers);

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
    if (response.status === 401 || response.status === 403) {
      const err = new Error("Invalid or expired API key. Check your widget configuration.");
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
    onMetadata?: (
      model: string,
      confidence: string,
      fromCache: boolean,
      conversationId?: string,
      confidenceScore?: number,
    ) => void;
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
              callbacks.onMetadata?.(
                data.model,
                data.confidence,
                data.from_cache ?? false,
                data.conversation_id,
                data.confidence_score,
              );
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
  // ── Chat: ask (SSE stream) — POST /api/v1/chat ────────────────────────────

  async askChatStream(
    body: {
      query: string;
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
      onMetadata: (
        model: string,
        confidence: string,
        fromCache?: boolean,
        conversationId?: string,
        confidenceScore?: number,
      ) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    },
  ) {
    try {
      const headers = new Headers({ "Content-Type": "application/json" });
      attachApiKey(headers);
      const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          const err = new Error("Invalid API key. Check widget configuration.");
          err.name = "AuthError";
          throw err;
        }
        if (response.status === 429 || response.status === 503) {
          const data = await response.json().catch(() => ({}));
          const err = new Error(
            data.detail?.message || data.detail || "Request limit reached",
          );
          err.name =
            response.status === 429 ? "RateLimitError" : "CapacityError";
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
    body: { content: string },
    callbacks: {
      onChunk: (content: string) => void;
      onMetadata: (
        model: string,
        confidence: string,
        fromCache?: boolean,
      ) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    },
  ) {
    try {
      const headers = new Headers({ "Content-Type": "application/json" });
      attachApiKey(headers);
      const response = await fetch(
        `${API_BASE_URL}/api/v1/chat/${conversationId}/message/${messageId}`,
        {
          method: "PATCH",
          headers,
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.detail || `Edit message failed: ${response.status}`,
        );
      }

      await consumeSseStream(response, callbacks);
    } catch (err) {
      callbacks.onError(err);
    }
  },

  // ── Chat: rename conversation ─────────────────────────────────────────────

  async updateConversationTitle(conversationId: string, title: string) {
    return fetchApi<void>(`/api/v1/chat/${conversationId}/title`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  },

  // ── Subjects ─────────────────────────────────────────────────────────────

  async getSubjects(board: string, classLevel: number) {
    return fetchApi(`/api/v1/subjects/${board}/${classLevel}`);
  },

  // ── Question Paper Generator — /api/v1/generate/question-paper ────────────

  async generatePaper(
    config: PaperConfig,
  ): Promise<{ paper_id: string; status: string }> {
    return fetchApi("/api/v1/generate/question-paper", {
      method: "POST",
      body: JSON.stringify(config),
    });
  },

  async listPapers(): Promise<{ papers: GeneratedPaper[] }> {
    return fetchApi("/api/v1/generate/question-paper");
  },

  async getPaper(id: string): Promise<GeneratedPaper> {
    return fetchApi(`/api/v1/generate/question-paper/${id}`);
  },

  async downloadPaper(id: string, variant: string, type: string): Promise<void> {
    const headers = new Headers();
    attachApiKey(headers);
    const response = await fetch(
      `${API_BASE_URL}/api/v1/generate/question-paper/${id}/download?variant=${encodeURIComponent(variant)}&type=${encodeURIComponent(type)}`,
      { headers },
    );
    if (!response.ok) throw new Error("Download failed");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const cd = response.headers.get("content-disposition") ?? "";
    const match = cd.match(/filename="([^"]+)"/);
    a.href = url;
    a.download = match ? match[1] : `paper_${type}.html`;
    a.click();
    URL.revokeObjectURL(url);
  },

  async deletePaper(id: string): Promise<{ status: string }> {
    return fetchApi(`/api/v1/generate/question-paper/${id}`, { method: "DELETE" });
  },

  // ── DPP / Worksheets — /api/v1/generate/dpp ──────────────────────────────

  async generateWorksheet(
    config: WorksheetConfig,
  ): Promise<{ worksheet_id: string; status: string }> {
    return fetchApi("/api/v1/generate/dpp", {
      method: "POST",
      body: JSON.stringify(config),
    });
  },

  async listWorksheets(): Promise<{ worksheets: GeneratedWorksheet[] }> {
    return fetchApi("/api/v1/generate/dpp");
  },

  async getWorksheet(id: string): Promise<GeneratedWorksheet> {
    return fetchApi(`/api/v1/generate/dpp/${id}`);
  },

  async downloadWorksheet(id: string, type: string): Promise<void> {
    const headers = new Headers();
    attachApiKey(headers);
    const response = await fetch(
      `${API_BASE_URL}/api/v1/generate/dpp/${id}/download?type=${encodeURIComponent(type)}`,
      { headers },
    );
    if (!response.ok) throw new Error("Download failed");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const cd = response.headers.get("content-disposition") ?? "";
    const match = cd.match(/filename="([^"]+)"/);
    a.href = url;
    a.download = match ? match[1] : `dpp_${type}.html`;
    a.click();
    URL.revokeObjectURL(url);
  },

  async deleteWorksheet(id: string): Promise<{ status: string }> {
    return fetchApi(`/api/v1/generate/dpp/${id}`, { method: "DELETE" });
  },

  // ── Util: client-side image compression ──────────────────────────────────

  async compressImageToBase64(
    file: File,
    maxWidth = 1000,
    maxHeight = 1000,
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let { width, height } = img;
          if (width > height) {
            if (width > maxWidth) {
              height = Math.round((height * maxWidth) / width);
              width = maxWidth;
            }
          } else {
            if (height > maxHeight) {
              width = Math.round((width * maxHeight) / height);
              height = maxHeight;
            }
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
