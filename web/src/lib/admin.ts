export type TicketStatus = "open" | "in_progress" | "resolved";

export interface AdminTicket {
  id: string;
  studentId: string;
  studentClass: string;
  questionText: string;
  questionImageUrl?: string;
  layer3Answer?: string;
  layer4Answer?: string;
  status: TicketStatus;
  createdAt: number;
}

const MOCK_TICKETS: AdminTicket[] = [
  {
    id: "TKT-0421-105",
    studentId: "9876543210",
    studentClass: "Class 10",
    questionText: "How does the heart pump blood? I didn't understand the diagram in the NCERT book.",
    status: "open",
    createdAt: Date.now() - 1000 * 60 * 15, // 15 mins ago
    layer4Answer: "The heart pumps blood through a continuous cycle of contraction and relaxation. The right atrium receives deoxygenated blood... (AI generated)"
  },
  {
    id: "TKT-0421-089",
    studentId: "9876543211",
    studentClass: "Class 12",
    questionText: "Please explain the derivation of Maxwell's equations. I am confused by Gauss's law for magnetism.",
    status: "in_progress",
    createdAt: Date.now() - 1000 * 60 * 120, // 2 hours ago
    layer3Answer: "Gauss's law for magnetism states that the net magnetic flux through any closed surface is zero. This implies that magnetic monopoles do not exist.",
  },
  {
    id: "TKT-0420-902",
    studentId: "9876543200",
    studentClass: "Class 9",
    questionText: "What is the difference between speed and velocity?",
    status: "resolved",
    createdAt: Date.now() - 1000 * 60 * 60 * 24, // 1 day ago
  }
];

export function getAdminTickets(): AdminTicket[] {
  // In a real app, this would fetch from an API
  const stored = localStorage.getItem("javaab.admin.tickets");
  if (!stored) {
    localStorage.setItem("javaab.admin.tickets", JSON.stringify(MOCK_TICKETS));
    return MOCK_TICKETS;
  }
  return JSON.parse(stored);
}

export function getTicketById(id: string): AdminTicket | undefined {
  return getAdminTickets().find(t => t.id === id);
}

export function getAdminStats() {
  const tickets = getAdminTickets();
  const openCount = tickets.filter(t => t.status === "open").length;
  const inProgressCount = tickets.filter(t => t.status === "in_progress").length;
  
  // Mock resolved today
  const resolvedToday = tickets.filter(t => 
    t.status === "resolved" && 
    (Date.now() - t.createdAt < 24 * 60 * 60 * 1000)
  ).length;

  return {
    openCount,
    inProgressCount,
    resolvedToday,
    avgResponseTime: 12, // mock 12 mins
  };
}

export function updateTicketStatus(id: string, status: TicketStatus) {
  const tickets = getAdminTickets();
  const idx = tickets.findIndex(t => t.id === id);
  if (idx !== -1) {
    tickets[idx].status = status;
    localStorage.setItem("javaab.admin.tickets", JSON.stringify(tickets));
  }
}

export function respondToTicket(id: string, response: string) {
  const tickets = getAdminTickets();
  const idx = tickets.findIndex(t => t.id === id);
  if (idx !== -1) {
    tickets[idx].status = "resolved";
    // realistically, response would be saved as well
    localStorage.setItem("javaab.admin.tickets", JSON.stringify(tickets));
  }
}
