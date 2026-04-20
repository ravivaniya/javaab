import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RequireAuth } from "@/components/RequireAuth";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Chat from "./pages/Chat";
import Subjects from "./pages/Subjects";
import Tickets from "./pages/Tickets";
import TicketDetail from "./pages/TicketDetail";
import Subscribe from "./pages/Subscribe";
import Refer from "./pages/Refer";
import SettingsSubscription from "./pages/SettingsSubscription";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

// Admin Portal Pages
import TeacherLayout from "./pages/admin/TeacherLayout";
import TeacherDashboard from "./pages/admin/TeacherDashboard";
import TeacherTickets from "./pages/admin/TeacherTickets";
import TeacherTicketDetail from "./pages/admin/TeacherTicketDetail";
import TeacherAnalytics from "./pages/admin/TeacherAnalytics";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/login" element={<Login />} />

          {/* Onboarding requires auth but NOT completed onboarding */}
          <Route
            path="/onboarding"
            element={
              <RequireAuth requireOnboarded={false}>
                <Onboarding />
              </RequireAuth>
            }
          />

          {/* App routes — auth + onboarded */}
          <Route path="/chat" element={<RequireAuth><Chat /></RequireAuth>} />
          <Route path="/subjects" element={<RequireAuth><Subjects /></RequireAuth>} />
          <Route path="/tickets" element={<RequireAuth><Tickets /></RequireAuth>} />
          <Route path="/tickets/:id" element={<RequireAuth><TicketDetail /></RequireAuth>} />
          <Route path="/subscribe" element={<RequireAuth><Subscribe /></RequireAuth>} />
          <Route path="/refer" element={<RequireAuth><Refer /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route
            path="/settings/subscription"
            element={<RequireAuth><SettingsSubscription /></RequireAuth>}
          />

          {/* Admin Routes */}
          <Route 
            path="/admin/teacher" 
            element={<RequireAuth requiredRole="teacher"><TeacherLayout /></RequireAuth>}
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<TeacherDashboard />} />
            <Route path="tickets" element={<TeacherTickets />} />
            <Route path="tickets/:id" element={<TeacherTicketDetail />} />
            <Route path="analytics" element={<TeacherAnalytics />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
