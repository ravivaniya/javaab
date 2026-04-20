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

  // Phase 1: No auth headers explicitly needed for these endpoints yet,
  // but if needed in Phase 2, they go here.
  
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
    // We can throw specifically for 429
    if (response.status === 429) {
      const err = new Error(message);
      err.name = "RateLimitError";
      throw err;
    }
    throw new Error(message);
  }

  return response.json();
}

/** Connect to backend logic */
export const ApiService = {
  // --- AUTH / PROFILE --- //
  
  async registerUser(data: { phone: string }) {
    return fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateProfile(data: Record<string, unknown>) {
    // We map student profile to a theoretical POST /student/profile endpoint 
    // replacing the local storage logic.
    return fetchApi("/student/profile", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // --- SUBJECTS --- //

  async getSubjects(board: string, classLevel: number) {
    return fetchApi(`/subjects/${board}/${classLevel}`);
  },

  // --- CHAT --- //

  async sendFeedback(messageId: string, isPositive: boolean, reason?: string) {
    return fetchApi("/chat/feedback", {
      method: "POST",
      body: JSON.stringify({
        message_id: messageId,
        is_positive: isPositive,
        reason: reason || "",
      }),
    });
  },

  /** 
   * Custom POST implementation to consume SSE manually.
   */
  async askChatStream(
    body: {
      query: string;
      user_id: string; // The phone number for now
      image_base64?: string;
      board: string;
      class_level: number;
      subject: string;
      language: string;
    },
    callbacks: {
      onChunk: (content: string) => void;
      onMetadata: (model: string, confidence: string) => void;
      onSources: (sources: Record<string, unknown>[]) => void;
      onDone: () => void;
      onError: (err: unknown) => void;
    }
  ) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        if (response.status === 429) {
          const data = await response.json().catch(() => ({}));
          const err = new Error(data.detail || "Rate limit exceeded");
          err.name = "RateLimitError";
          throw err;
        }
        throw new Error(`Chat API failed: ${response.status}`);
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // SSE are delimited by \n\n
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          
          if (chunk.startsWith("data: ")) {
            const dataStr = chunk.replace(/^data:\s*/, "");
            if (dataStr === "[DONE]") {
              callbacks.onDone();
            } else {
              try {
                const data = JSON.parse(dataStr);
                if (data.type === "chunk") {
                  callbacks.onChunk(data.content);
                } else if (data.type === "metadata") {
                  callbacks.onMetadata(data.model, data.confidence);
                } else if (data.type === "sources") {
                  callbacks.onSources(data.sources);
                } else if (data.type === "done") {
                  callbacks.onDone();
                }
              } catch (e) {
                console.error("Failed to parse SSE line:", chunk, e);
              }
            }
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
      // Ensure onDone is called if not explicitly sent in the stream
      callbacks.onDone();
    } catch (err) {
      callbacks.onError(err);
    }
  },

  /** Util for Client Side image base64 + compression */
  async compressImageToBase64(file: File, maxWidth = 1000, maxHeight = 1000): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          let width = img.width;
          let height = img.height;

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
          
          // Return base64 without the mime prefix as backend expects raw base64
          // Wait, backend expects full base64 or just raw? Usually standard is raw or split.
          // In ChatRequest it asks for base64. Typically raw.
          const dataUrl = canvas.toDataURL(file.type, 0.85); // 85% quality WEBP/JPEG
          const base64Data = dataUrl.split(",")[1];
          resolve(base64Data);
        };
        img.onerror = reject;
        img.src = e.target?.result as string;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
};
