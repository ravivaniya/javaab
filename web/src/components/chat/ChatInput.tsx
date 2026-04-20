import { useRef, useState, KeyboardEvent } from "react";
import { Camera, ImagePlus, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UpgradeModal } from "./UpgradeModal";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (text: string, imageUrl?: string) => void;
  disabled?: boolean;
  isPaid: boolean;
  placeholder?: string;
}

/** Pill-shaped chat composer with camera/gallery (Plus+) and send. */
export function ChatInput({ onSend, disabled, isPaid, placeholder }: Props) {
  const [text, setText] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!text.trim() || disabled) return;
    onSend(text, imageUrl ?? undefined);
    setText("");
    setImageUrl(null);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onPickFile = () => {
    if (!isPaid) {
      setUpgradeOpen(true);
      return;
    }
    fileRef.current?.click();
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    e.target.value = "";
  };

  return (
    <>
      <div className="mx-auto w-full max-w-3xl">
        <div
          className={cn(
            "flex flex-col gap-2 rounded-3xl border bg-card p-2 shadow-md transition-all",
            "focus-within:border-primary/40 focus-within:shadow-lg",
            disabled && "opacity-60",
          )}
        >
          {imageUrl && (
            <div className="relative ml-1 mt-1 inline-block w-fit">
              <img
                src={imageUrl}
                alt="Preview"
                className="h-16 w-16 rounded-xl object-cover"
              />
              <button
                onClick={() => setImageUrl(null)}
                className="absolute -right-1.5 -top-1.5 rounded-full bg-foreground text-background"
                aria-label="Remove image"
              >
                <X className="h-4 w-4 p-0.5" />
              </button>
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
              rows={1}
              placeholder={placeholder ?? "पूछो कुछ भी... Ask anything..."}
              disabled={disabled}
              className="max-h-40 min-h-[40px] flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-[15px] text-foreground placeholder:text-muted-foreground focus:outline-none"
            />

            <Button
              type="button"
              size="icon"
              onClick={submit}
              disabled={!text.trim() || disabled}
              className="h-10 w-10 shrink-0 rounded-full"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>

          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={onFile}
          />
        </div>
      </div>

      <UpgradeModal
        open={upgradeOpen}
        onOpenChange={setUpgradeOpen}
        feature="Image input"
      />
    </>
  );
}
