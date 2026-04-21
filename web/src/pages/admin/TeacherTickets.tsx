import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AdminTicket, getAdminTickets, TicketStatus } from "@/lib/admin";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDistanceToNow } from "date-fns";

export default function TeacherTickets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState<AdminTicket[]>([]);

  const currentStatus = searchParams.get("status") || "all";
  const currentSort = searchParams.get("sort") || "oldest";

  useEffect(() => {
    setTickets(getAdminTickets());
  }, []);

  const handleFilterChange = (key: string, value: string) => {
    setSearchParams(prev => {
      if (value === "all" || value === "") {
        prev.delete(key);
      } else {
        prev.set(key, value);
      }
      return prev;
    });
  };

  const filteredTickets = tickets.filter(t => {
    if (currentStatus !== "all" && t.status !== currentStatus) return false;
    return true;
  }).sort((a, b) => {
    if (currentSort === "oldest") return a.createdAt - b.createdAt;
    return b.createdAt - a.createdAt; // newest
  });

  const getStatusBadge = (status: TicketStatus) => {
    switch (status) {
      case "open":
        return <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-0">Open</Badge>;
      case "in_progress":
        return <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-0">In Progress</Badge>;
      case "resolved":
        return <Badge className="bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] hover:bg-[hsl(var(--success))]/20 border-0">Resolved</Badge>;
    }
  };

  return (
    <div className="flex h-full flex-col p-4 sm:p-8 animate-fade-in">
      <div className="mb-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight">Active Tickets</h1>
          <p className="text-muted-foreground mt-1">Review and intercept student doubts directly.</p>
        </div>
        
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">

          <Select value={currentStatus} onValueChange={(v) => handleFilterChange("status", v)}>
            <SelectTrigger className="w-full sm:w-[140px] bg-background">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
          <Select value={currentSort} onValueChange={(v) => handleFilterChange("sort", v)}>
            <SelectTrigger className="w-full sm:w-[140px] bg-background">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="newest">Newest First</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex-1 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="h-full overflow-auto">
          <Table>
            <TableHeader className="bg-muted/50 sticky top-0 z-10">
              <TableRow>
                <TableHead className="w-[100px]">ID</TableHead>
                <TableHead>Class</TableHead>

                <TableHead className="max-w-[300px]">Question Preview</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Wait Time</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    No tickets found matching your filters.
                  </TableCell>
                </TableRow>
              ) : (
                filteredTickets.map((ticket) => (
                  <TableRow key={ticket.id} className="hover:bg-muted/30">
                    <TableCell className="font-semibold">{ticket.id}</TableCell>
                    <TableCell>{ticket.studentClass}</TableCell>
                    <TableCell className="max-w-[300px] truncate text-muted-foreground">
                      {ticket.questionText}
                    </TableCell>
                    <TableCell>{getStatusBadge(ticket.status)}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
                      {formatDistanceToNow(ticket.createdAt, { addSuffix: true })}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm" variant={ticket.status === 'resolved' ? 'outline' : 'default'} className="rounded-pill">
                        <Link to={`/admin/teacher/tickets/${ticket.id}`}>
                          {ticket.status === 'resolved' ? 'Review' : 'Respond'}
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
