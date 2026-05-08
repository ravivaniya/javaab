import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { RequireAuth } from "@/components/RequireAuth";
import Index from "./pages/Index";
import Onboarding from "./pages/Onboarding";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import PapersList from "./pages/admin/Papers/PapersList";
import CreatePaper from "./pages/admin/Papers/CreatePaper";
import PaperDetail from "./pages/admin/Papers/PaperDetail";
import WorksheetsList from "./pages/admin/Worksheets/WorksheetsList";
import CreateWorksheet from "./pages/admin/Worksheets/CreateWorksheet";
import WorksheetDetail from "./pages/admin/Worksheets/WorksheetDetail";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />

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
            <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />

            {/* Admin — papers */}
            <Route path="/admin/papers" element={<RequireAuth><PapersList /></RequireAuth>} />
            <Route path="/admin/papers/new" element={<RequireAuth><CreatePaper /></RequireAuth>} />
            <Route path="/admin/papers/:id" element={<RequireAuth><PaperDetail /></RequireAuth>} />

            {/* Admin — worksheets */}
            <Route path="/admin/worksheets" element={<RequireAuth><WorksheetsList /></RequireAuth>} />
            <Route path="/admin/worksheets/new" element={<RequireAuth><CreateWorksheet /></RequireAuth>} />
            <Route path="/admin/worksheets/:id" element={<RequireAuth><WorksheetDetail /></RequireAuth>} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
