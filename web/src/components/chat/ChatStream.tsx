import { useState, useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { RateLimitCard } from "./RateLimitCard";
import { ApiService } from "@/services/api";
import type { ChatMessage, Confidence } from "@/lib/chat";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

type StreamSource = {
  title?: string;
  book?: string;
  chapter?: string;
};

export interface ChatStreamRequest {
  query: string;
  imageBase64?: string;
  board: string;
  classLevel: number;
  subject: string;
  language: string;
}

interface Props {
  request: ChatStreamRequest;
  userId: string;
  plan: string;
  usageCount: number;
  onComplete: (msg: ChatMessage) => void;
  onError?: (err: Error) => void;
}

export function ChatStream({
  request,
  userId,
  plan,
  usageCount,
  onComplete,
  onError,
}: Props) {
  const [content, setContent] = useState("");
  const [err, setErr] = useState<Error | null>(null);
  const [confidence, setConfidence] = useState<Confidence | undefined>();
  const [source, setSource] = useState<{ book: string; chapter: string } | undefined>();
  const [isDone, setIsDone] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const startStream = () => {
    setErr(null);
    setContent("");
    setIsDone(false);

    ApiService.askChatStream(
      {
        query: request.query,
        user_id: userId,
        image_base64: request.imageBase64,
        board: request.board,
        class_level: request.classLevel,
        subject: request.subject,
        language: request.language,
      },
      {
        onChunk: (chunk) => {
          setContent((prev) => prev + chunk);
        },
        onMetadata: (_model, conf) => {
          const c = conf?.toLowerCase() as Confidence;
          if (["verified", "ai", "low"].includes(c)) {
            setConfidence(c);
          }
        },
        onSources: (sources) => {
          if (sources && sources.length > 0) {
            const first = sources[0] as StreamSource;
            setSource({
              book: first.title || first.book || "Textbook",
              chapter: first.chapter || "",
            });
          }
        },
        onDone: () => {
          setIsDone(true);
        },
        onError: (e: unknown) => {
          const error = e instanceof Error ? e : new Error("A network error occurred.");
          setErr(error);
          if (onError) onError(error);
        },
      }
    );
  };

  useEffect(() => {
    startStream();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);

  useEffect(() => {
    if (isDone && !err) {
      onComplete({
        id: crypto.randomUUID(),
        role: "assistant",
        content,
        createdAt: Date.now(),
        confidence,
        source,
      });
    }
  }, [isDone, err, onComplete, content, confidence, source]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [content]);

  if (err && err.name === "RateLimitError") {
    return <RateLimitCard used={usageCount} plan={plan} />;
  }

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

  const tempMessage: ChatMessage = {
    id: "stream",
    role: "assistant",
    content,
    createdAt: Date.now(),
    confidence,
    source,
  };

  return (
    <div className="w-full pb-4">
      <MessageBubble message={tempMessage} />
      <div ref={scrollRef} className="h-4" />
    </div>
  );
}
