import { useEffect, useState } from "react";
import { getAdminStats } from "@/lib/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock, CheckCircle2, Ticket as TicketIcon, BookOpen, Layers, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function TeacherDashboard() {
  const [stats, setStats] = useState({
    openCount: 0,
    inProgressCount: 0,
    resolvedToday: 0,
    avgResponseTime: 0,
  });
  
  const navigate = useNavigate();

  useEffect(() => {
    setStats(getAdminStats());
  }, []);

  const statCards = [
    {
      title: "Open Tickets",
      value: stats.openCount,
      icon: TicketIcon,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
      param: "?status=open"
    },
    {
      title: "In Progress",
      value: stats.inProgressCount,
      icon: Clock,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
      param: "?status=in_progress"
    },
    {
      title: "Resolved Today",
      value: stats.resolvedToday,
      icon: CheckCircle2,
      color: "text-[hsl(var(--success))]",
      bg: "bg-[hsl(var(--success))]/10",
      param: "?status=resolved"
    },
    {
      title: "Avg Response",
      value: `${stats.avgResponseTime}m`,
      icon: Zap,
      color: "text-purple-500",
      bg: "bg-purple-500/10",
      param: ""
    },
  ];

  return (
    <div className="p-4 sm:p-8 space-y-8 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground mt-1">
          Monitor your queue and track recent student queries.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card 
            key={card.title} 
            className={`cursor-pointer transition-all hover:shadow-md hover:border-primary/50`}
            onClick={() => card.param && navigate(`/admin/teacher/tickets${card.param}`)}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className={`rounded-xl p-2 ${card.bg}`}>
                <card.icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <div className="pt-4">
        <h2 className="font-display text-xl font-bold tracking-tight mb-4">Quick Filters</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
           <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/admin/teacher/tickets?subject=Mathematics')}>
             <CardContent className="flex items-center gap-4 p-6">
               <div className="rounded-xl bg-primary/10 p-3">
                 <BookOpen className="h-5 w-5 text-primary" />
               </div>
               <div>
                 <p className="font-bold">Mathematics</p>
                 <p className="text-sm text-muted-foreground">Filter active math doubts</p>
               </div>
             </CardContent>
           </Card>

           <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/admin/teacher/tickets?subject=Science')}>
             <CardContent className="flex items-center gap-4 p-6">
               <div className="rounded-xl bg-primary/10 p-3">
                 <Layers className="h-5 w-5 text-primary" />
               </div>
               <div>
                 <p className="font-bold">Science</p>
                 <p className="text-sm text-muted-foreground">Filter active science queries</p>
               </div>
             </CardContent>
           </Card>

           <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/admin/teacher/tickets?status=open&sort=oldest')}>
             <CardContent className="flex items-center gap-4 p-6">
               <div className="rounded-xl bg-[hsl(var(--warning))]/10 p-3">
                 <Clock className="h-5 w-5 text-[hsl(var(--warning))]" />
               </div>
               <div>
                 <p className="font-bold">High Urgency</p>
                 <p className="text-sm text-muted-foreground">Oldest open tickets</p>
               </div>
             </CardContent>
           </Card>
        </div>
      </div>
    </div>
  );
}
