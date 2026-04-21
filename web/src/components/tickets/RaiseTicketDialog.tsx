import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createTicket } from "@/lib/tickets";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function RaiseTicketDialog({ open, onOpenChange }: Props) {
  const { user } = useAuth();
  const { toast } = useToast();
  const nav = useNavigate();
  const [question, setQuestion] = useState("");
  const [aiAttempt, setAiAttempt] = useState("");

  const submit = () => {
    if (!user || !question.trim()) return;
    const t = createTicket(user.phone, {
      question: question.trim(),
      aiAttempt: aiAttempt.trim() || undefined,
    });
    toast({
      title: "Ticket raised 🎓",
      description: `${t.id} — a verified teacher will reply soon.`,
    });
    setQuestion("");
    setAiAttempt("");
    onOpenChange(false);
    nav(`/tickets/${t.id}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl font-black">
            Raise a teacher ticket
          </DialogTitle>
          <DialogDescription>
            A verified teacher will personally answer within 24 hours. Use this when AI's answer
            isn't enough.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">

          <div>
            <Label htmlFor="t-q" className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Your question
            </Label>
            <Textarea
              id="t-q"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Describe what you're stuck on. Be specific."
              rows={4}
            />
          </div>

          <div>
            <Label htmlFor="t-ai" className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              AI's attempt (optional)
            </Label>
            <Input
              id="t-ai"
              value={aiAttempt}
              onChange={(e) => setAiAttempt(e.target.value)}
              placeholder="Paste what the AI said, if anything"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!question.trim()} className="rounded-pill">
            Submit ticket
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
