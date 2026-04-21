import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getTicketById,
  respondToTicket,
  updateTicketStatus,
} from "@/lib/admin";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  CheckCircle,
  Image as ImageIcon,
  Send,
  Sparkles,
} from "lucide-react";
import { MarkdownWithMath } from "@/components/chat/MarkdownWithMath";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

export default function TeacherTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(getTicketById(id || ""));
  const [replyText, setReplyText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (!ticket) {
      navigate("/admin/teacher/tickets");
      return;
    }
    // Auto-mark as in_progress if currently open
    if (ticket.status === "open") {
      updateTicketStatus(ticket.id, "in_progress");
      setTicket((prev) => (prev ? { ...prev, status: "in_progress" } : prev));
    }
  }, [ticket, navigate]);

  if (!ticket) return null;

  const handleSubmit = async () => {
    if (!replyText.trim()) {
      toast.error("Please enter a response.");
      return;
    }
    setIsSubmitting(true);
    // Simulate API network latency
    await new Promise((r) => setTimeout(r, 600));

    respondToTicket(ticket.id, replyText);

    toast.success(
      "Answer sent! Also cached so future students get instant answers for this question.",
      {
        duration: 5000,
        icon: <CheckCircle className="text-[hsl(var(--success))]" />,
      },
    );

    navigate("/admin/teacher/tickets");
  };

  return (
    <div className="flex h-full flex-col overflow-hidden animate-fade-in">
      {/* Header */}
      <header className="flex shrink-0 items-center gap-4 bg-background px-4 py-4 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/admin/teacher/tickets")}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex flex-1 items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight">
              Review Ticket #{ticket.id}
            </h1>
            <p className="text-sm text-muted-foreground">
              {ticket.studentClass} •{" "}
              {formatDistanceToNow(ticket.createdAt, { addSuffix: true })}
            </p>
          </div>
          <Badge
            variant={ticket.status === "resolved" ? "secondary" : "default"}
            className="rounded-full px-3 py-1 text-sm bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-0"
          >
            {ticket.status === "resolved" ? "Resolved" : "In Progress"}
          </Badge>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
        <div className="mx-auto grid gap-6 xl:grid-cols-[1fr_1fr]">
          {/* Left Column: Student Context */}
          <div className="space-y-6">
            {/* Student Question */}
            <Card className="border-primary/20 shadow-sm bg-primary/5">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-primary uppercase tracking-wider">
                  Student Question
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="whitespace-pre-wrap font-medium leading-relaxed">
                  {ticket.questionText}
                </p>
                {ticket.questionImageUrl && (
                  <div className="mt-4 rounded-xl overflow-hidden border">
                    <img
                      src={ticket.questionImageUrl}
                      alt="Student Upload"
                      className="object-cover w-full max-h-60"
                    />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* AI Attempts */}
            <div className="space-y-4">
              <h3 className="font-semibold flex items-center gap-2 text-muted-foreground px-1">
                <Sparkles className="h-4 w-4" /> AI Layer Attempts
              </h3>

              {ticket.layer3Answer ? (
                <Card className="bg-muted/40 border-dashed">
                  <CardHeader className="pb-2">
                    <CardDescription className="font-mono text-xs font-semibold text-foreground/60">
                      Semantic Match (L3)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm text-foreground/80">
                    <MarkdownWithMath>{ticket.layer3Answer}</MarkdownWithMath>
                  </CardContent>
                </Card>
              ) : (
                <p className="text-xs text-muted-foreground px-2">
                  No Layer 3 answer logged.
                </p>
              )}

              {ticket.layer4Answer && (
                <Card className="bg-muted/40 border-dashed">
                  <CardHeader className="pb-2">
                    <CardDescription className="font-mono text-xs font-semibold text-foreground/60">
                      LLM Generation (L4)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm text-foreground/80">
                    <MarkdownWithMath>{ticket.layer4Answer}</MarkdownWithMath>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Right Column: Teacher Output */}
          <div className="flex flex-col h-full space-y-4">
            <div className="flex items-center justify-between px-1">
              <h2 className="font-display text-lg font-bold">
                Your Official Answer
              </h2>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={showPreview ? "default" : "secondary"}
                  className="rounded-full text-xs h-8"
                  onClick={() => setShowPreview(true)}
                >
                  Preview
                </Button>
                <Button
                  size="sm"
                  variant={!showPreview ? "default" : "secondary"}
                  className="rounded-full text-xs h-8"
                  onClick={() => setShowPreview(false)}
                >
                  Edit
                </Button>
              </div>
            </div>

            <Card className="flex-1 flex flex-col min-h-[400px]">
              <CardContent className="p-0 flex-1 flex flex-col relative overflow-hidden">
                {showPreview ? (
                  <div className="flex-1 overflow-y-auto p-4 bg-muted/20">
                    {replyText.trim() ? (
                      <MarkdownWithMath>{replyText}</MarkdownWithMath>
                    ) : (
                      <p className="text-muted-foreground text-sm italic">
                        Type your Markdown or LaTeX response to see a preview...
                      </p>
                    )}
                  </div>
                ) : (
                  <Textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Provide the definitive answer using Markdown or LaTeX ($$E=mc^2$$)..."
                    className="flex-1 resize-none border-0 focus-visible:ring-0 p-4 min-h-[300px] leading-relaxed"
                  />
                )}
              </CardContent>
              <div className="flex items-center justify-between border-t border-border p-3 bg-muted/10">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-full gap-2 text-muted-foreground"
                >
                  <ImageIcon className="h-4 w-4" />
                  Upload Image
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={
                    isSubmitting ||
                    !replyText.trim() ||
                    ticket.status === "resolved"
                  }
                  className="rounded-full px-6 gap-2 shadow-sm font-semibold"
                >
                  {isSubmitting ? (
                    "Caching..."
                  ) : ticket.status === "resolved" ? (
                    "Already Resolved"
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Approve & Send
                    </>
                  )}
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
