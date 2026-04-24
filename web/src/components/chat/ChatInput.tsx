import { useRef, useState, KeyboardEvent, ClipboardEvent } from "react";
import { toast } from "@/hooks/use-toast";
import { Camera, ImagePlus, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UpgradeModal } from "./UpgradeModal";
import { cn } from "@/lib/utils";

const WORD_LIMIT = 150;
const WORD_WARN_THRESHOLD = 130;
const WORD_DANGER_THRESHOLD = 148;
const SESSION_WARN_THRESHOLD = 7000;
const SESSION_LIMIT = 7500;

interface Props {
  onSend: (text: string, imageUrl?: string) => void;
  disabled?: boolean;
  isPaid: boolean;
  placeholder?: string;
  /** Cumulative words used in this session (for H session limit banner). */
  sessionWordCount?: number;
  /** Called when user clicks "Start new chat" in the session limit message. */
  onNewChat?: () => void;
}

/** Pill-shaped chat composer with image attach, word count, and send. */
export function ChatInput({ onSend, disabled, isPaid, placeholder, sessionWordCount = 0, onNewChat }: Props) {
  const [text, setText] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [hoverPreview, setHoverPreview] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const wordCount = text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0;
  const overLimit = wordCount > WORD_LIMIT;
  const sessionAtLimit = sessionWordCount >= SESSION_LIMIT;
  const sessionNearLimit = sessionWordCount >= SESSION_WARN_THRESHOLD && !sessionAtLimit;

  const submit = () => {
    if (!text.trim() || disabled || overLimit || sessionAtLimit) return;
    onSend(text, imageBase64 || undefined);
    setText("");
    setImageUrl(null);
    setImageBase64(null);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onPickFile = () => {
    if (!isPaid) { setUpgradeOpen(true); return; }
    fileRef.current?.click();
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    try {
      const { ApiService } = await import("@/services/api");
      const base64 = await ApiService.compressImageToBase64(file);
      setImageBase64(base64);
    } catch (err) {
      console.error("Failed to compress image", err);
    }
    e.target.value = "";
  };

  const onPaste = async (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        if (!isPaid) { e.preventDefault(); setUpgradeOpen(true); return; }
        const file = item.getAsFile();
        if (!file) continue;
        e.preventDefault();
        const url = URL.createObjectURL(file);
        setImageUrl(url);
        try {
          const { ApiService } = await import("@/services/api");
          const base64 = await ApiService.compressImageToBase64(file);
          setImageBase64(base64);
        } catch (err) {
          console.error("Failed to compress pasted image", err);
        }
        toast({ title: "Image pasted", description: "Ready to send with your message." });
        return;
      }
    }
  };

  // Word count color
  const wordCountClass = overLimit
    ? "text-red-500"
    : wordCount >= WORD_DANGER_THRESHOLD
      ? "text-red-400"
      : wordCount >= WORD_WARN_THRESHOLD
        ? "text-orange-500"
        : "text-muted-foreground";

  return (
    <>
      <div className="mx-auto w-full max-w-3xl space-y-2">
        {/* Session near-limit warning banner */}
        {sessionNearLimit && (
          <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-2 text-sm text-amber-800 dark:text-amber-300">
            Conversation nearing its limit. Start a new chat to continue fresh.
          </div>
        )}

        <div
          className={cn(
            "flex flex-col gap-2 rounded-3xl border bg-card p-2 shadow-md transition-all",
            "focus-within:border-primary/40 focus-within:shadow-lg",
            disabled && "opacity-60",
          )}
        >
          {/* Image thumbnail preview */}
          {imageUrl && (
            <div
              className="relative ml-1 mt-1 inline-block w-fit"
              onMouseEnter={() => setHoverPreview(true)}
              onMouseLeave={() => setHoverPreview(false)}
            >
              <img src={imageUrl} alt="Preview" className="h-16 w-16 rounded-xl object-cover cursor-pointer" />
              <button
                onClick={() => { setImageUrl(null); setImageBase64(null); }}
                className="absolute -right-1.5 -top-1.5 rounded-full bg-foreground text-background"
                aria-label="Remove image"
              >
                <X className="h-4 w-4 p-0.5" />
              </button>
              {/* Hover popover — larger preview */}
              {hoverPreview && (
                <div className="absolute bottom-full left-0 mb-2 z-10">
                  <img src={imageUrl} alt="Preview large" className="h-48 w-48 rounded-xl object-cover shadow-lg border border-border" />
                </div>
              )}
            </div>
          )}

          <div className="flex items-end gap-1.5">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:text-primary"
              onClick={onPickFile}
              aria-label="Attach photo"
              disabled={disabled}
            >
              <Camera className="h-5 w-5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-full text-muted-foreground hover:text-primary"
              onClick={onPickFile}
              aria-label="Attach image"
              disabled={disabled}
            >
              <ImagePlus className="h-5 w-5" />
            </Button>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKey}
              onPaste={onPaste}
              rows={1}
              placeholder={placeholder ?? "पूछो कुछ भी... Ask anything..."}
              disabled={disabled || sessionAtLimit}
              className="max-h-40 min-h-[40px] flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-[15px] text-foreground placeholder:text-muted-foreground focus:outline-none"
            />

            <Button
              type="button"
              size="icon"
              onClick={submit}
              disabled={!text.trim() || disabled || overLimit || sessionAtLimit}
              className="h-10 w-10 shrink-0 rounded-full"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>

          {/* Word count indicator */}
          {(wordCount > 0 || overLimit) && (
            <div className={cn("flex justify-end pr-2 pb-1 text-[11px] font-medium", wordCountClass)}>
              {wordCount} / {WORD_LIMIT} words
            </div>
          )}

          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
        </div>

        {/* Session at-limit inline message */}
        {sessionAtLimit && (
          <div className="rounded-xl bg-muted px-4 py-3 text-sm text-muted-foreground">
            This session has reached its limit.{" "}
            <button
              onClick={onNewChat}
              className="font-medium text-primary underline-offset-2 hover:underline"
            >
              Start new chat →
            </button>
          </div>
        )}
      </div>

      <UpgradeModal open={upgradeOpen} onOpenChange={setUpgradeOpen} feature="Image input" />
    </>
  );
}
