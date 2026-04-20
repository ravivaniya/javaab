import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { Sparkles, TrendingUp, Users } from "lucide-react";

export default function TeacherAnalytics() {
  // Hardcoded mock data for presentation purposes
  const resolutionTrendData = [
    { name: "Mon", time: 45 },
    { name: "Tue", time: 38 },
    { name: "Wed", time: 41 },
    { name: "Thu", time: 30 },
    { name: "Fri", time: 25 },
    { name: "Sat", time: 18 },
    { name: "Sun", time: 15 },
  ];

  const topicMixData = [
    { name: "Mathematics", value: 400 },
    { name: "Physics", value: 300 },
    { name: "Chemistry", value: 200 },
    { name: "Biology", value: 278 },
  ];
  
  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'];

  const monthlyTickets = [
    { name: "Week 1", answered: 120 },
    { name: "Week 2", answered: 145 },
    { name: "Week 3", answered: 132 },
    { name: "Week 4", answered: 180 },
  ];

  return (
    <div className="flex h-full flex-col p-4 sm:p-8 animate-fade-in pb-12">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold tracking-tight">Analytics Center</h1>
        <p className="text-muted-foreground mt-1">
          Monitor your impact across student cohorts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Tickets Answered (Month)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black flex items-center justify-between">
              577
              <TrendingUp className="h-5 w-5 text-[hsl(var(--success))]" />
            </div>
            <p className="text-xs text-[hsl(var(--success))] font-medium mt-1">+12% from last month</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Average Rating</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black flex items-center justify-between">
              4.8<span className="text-sm text-muted-foreground font-medium">/ 5.0</span>
              <Sparkles className="h-5 w-5 text-amber-500" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">Based on 342 reviews</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">Active Students Reached</CardTitle>
          </CardHeader>
          <CardContent>
             <div className="text-3xl font-black flex items-center justify-between">
              2,410
              <Users className="h-5 w-5 text-primary" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">Across 8 states</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="col-span-1 shadow-sm">
          <CardHeader>
            <CardTitle>Resolution Time Trend (Mins)</CardTitle>
            <CardDescription>Average time taken to resolve a ticket gracefully.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={resolutionTrendData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ borderRadius: "8px", border: "1px solid hsl(var(--border))", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                />
                <Line type="monotone" dataKey="time" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="col-span-1 shadow-sm">
          <CardHeader>
            <CardTitle>Common Topics Mix</CardTitle>
            <CardDescription>Volume of tickets categorized by subject layer.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center">
             <ResponsiveContainer width="100%" height="100%">
               <PieChart>
                  <Pie
                    data={topicMixData}
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {topicMixData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: "8px", border: "1px solid hsl(var(--border))" }}
                  />
               </PieChart>
             </ResponsiveContainer>
             <div className="flex flex-col gap-2 shrink-0">
               {topicMixData.map((entry, index) => (
                 <div key={entry.name} className="flex items-center gap-2 text-sm font-medium">
                   <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                   {entry.name}
                 </div>
               ))}
             </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2 shadow-sm">
           <CardHeader>
            <CardTitle>Tickets Answered Progression</CardTitle>
            <CardDescription>Gross volume of manual overrides executed.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyTickets} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground)/0.2)" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <Tooltip 
                  cursor={{ fill: 'hsl(var(--muted)/0.4)' }}
                  contentStyle={{ borderRadius: "8px", border: "1px solid hsl(var(--border))" }}
                />
                <Bar dataKey="answered" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
