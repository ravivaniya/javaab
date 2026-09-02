import { useState, useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { TypingDots } from "./TypingDots";
import { ApiService } from "@/services/api";
import type { ChatMessage, Confidence } from "@/lib/chat";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

type StreamSource = {
  title?: string;
  book?: string;
  chapter?: string;
};

const MODEL_LABELS: Record<string, string> = {
  "gpt-41-nano": "Quick Answer",
  "gpt-41-mini": "GPT-4.1 Mini",
  "gpt-41": "GPT-4.1",
  "cache": "Verified Answer",
};

export interface ChatStreamRequest {
  query: string;
  imageBase64?: string;
  board: string;
  classLevel: number;
  subject: string;
  language: string;
  conversationId?: string;
  retryOf?: string;
  editMessageId?: string;
}

interface Props {
  request: ChatStreamRequest;
  onComplete: (msg: ChatMessage) => void;
  onError?: (err: Error) => void;
}

function stripFollowUpLines(text: string): string {
  return text
    .split("\n")
    .filter((line) => {
      const t = line.trim().toLowerCase();
      return !t.startsWith("would you like") && !t.startsWith("want to try");
    })
    .join("\n")
    .trimEnd();
}

export function ChatStream({ request, onComplete, onError }: Props) {
  const [content, setContent] = useState("");
  const [err, setErr] = useState<Error | null>(null);
  const [confidence, setConfidence] = useState<Confidence | undefined>();
  const [modelName, setModelName] = useState<string | undefined>();
  const [source, setSource] = useState<{ book: string; chapter: string } | undefined>();
  const [fromCache, setFromCache] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageIdRef = useRef(crypto.randomUUID());

  const startStream = () => {
    setErr(null);
    setContent("");
    setIsDone(false);
    setFromCache(false);
    messageIdRef.current = crypto.randomUUID();

    const commonCallbacks = {
      onChunk: (chunk: string) => setContent((prev) => prev + chunk),
      onMetadata: (model: string, conf: string, fc?: boolean, convId?: string, score?: number) => {
        if (model) setModelName(model);
        setFromCache(fc ?? false);
        const c = conf?.toLowerCase();
        const confMap: Record<string, Confidence> = {
          high: fc ? "verified" : "ai",
          medium: "ai",
          low: "low",
          none: "ai",
        };
        setConfidence(confMap[c] ?? "ai");
        console.log(
          `[javaab] conv=${convId ?? "?"} model=${model} conf=${conf} score=${score ?? 0} cache=${fc ?? false}`,
        );
      },
      onSources: (sources: Record<string, unknown>[]) => {
        if (sources?.length) {
          const first = sources[0] as StreamSource;
          setSource({ book: first.title || first.book || "Textbook", chapter: first.chapter || "" });
        }
      },
      onDone: () => setIsDone(true),
      onError: (e: unknown) => {
        const error = e instanceof Error ? e : new Error("A network error occurred.");
        setErr(error);
        onError?.(error);
      },
    };

    if (request.editMessageId) {
      ApiService.editMessageStream(
        request.conversationId!,
        request.editMessageId,
        { content: request.query },
        commonCallbacks,
      );
    } else {
      ApiService.askChatStream(
        {
          query: request.query,
          image_base64: request.imageBase64,
          board: request.board,
          class_level: request.classLevel,
          subject: request.subject,
          language: request.language,
          conversation_id: request.conversationId,
          retry_of: request.retryOf,
        },
        commonCallbacks,
      );
    }
  };

  useEffect(() => {
    startStream();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);

  useEffect(() => {
    if (isDone && !err) {
      const rawAnswer = stripFollowUpLines(content);
      onComplete({
        id: messageIdRef.current,
        role: "assistant",
        content,
        rawAnswer,
        createdAt: Date.now(),
        confidence,
        source,
        modelName,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDone, err]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [content]);

  void fromCache; // used in metadata callback above

  const modelLabel = modelName ? (MODEL_LABELS[modelName] ?? modelName) : undefined;

  if (err) {
    return (
      <div className="flex w-full justify-start animate-fade-in mb-4">
        <div className="max-w-[85%] space-y-3 rounded-2xl bg-destructive/10 px-5 py-4 text-destructive sm:max-w-[75%]">
          <p className="text-sm font-medium">{err.message || "A network error occurred."}</p>
          <Button variant="outline" size="sm" onClick={startStream} className="rounded-pill">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!content && !isDone) {
    return (
      <div className="flex w-full justify-start animate-fade-in mb-4">
        <div className="max-w-[92%] space-y-3 rounded-3xl rounded-tl-md bg-card px-5 py-4 shadow-sm ring-1 ring-border/50 sm:max-w-[80%]">
          <TypingDots modelHint={modelLabel} />
        </div>
      </div>
    );
  }

  const tempMessage: ChatMessage = {
    id: "stream",
    role: "assistant",
    content,
    rawAnswer: stripFollowUpLines(content),
    createdAt: Date.now(),
    confidence,
    source,
    modelName,
  };

  return (
    <div className="w-full pb-4">
      <MessageBubble message={tempMessage} />
      <div ref={scrollRef} className="h-4" />
    </div>
  );
}
