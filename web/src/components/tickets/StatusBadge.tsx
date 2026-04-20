import { Check, Clock, Eye } from "lucide-react";
import type { TicketStatus } from "@/lib/tickets";
import { cn } from "@/lib/utils";

const MAP: Record<TicketStatus, { label: string; cls: string; Icon: typeof Clock }> = {
  open:         { label: "Open",         cls: "bg-warning/15 text-warning",   Icon: Clock },
  with_teacher: { label: "With Teacher", cls: "bg-cbse/15 text-cbse",         Icon: Eye },
  answered:     { label: "Answered",     cls: "bg-success/15 text-success",   Icon: Check },
};

export function StatusBadge({ status, className }: { status: TicketStatus; className?: string }) {
  const { label, cls, Icon } = MAP[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold",
        cls,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
