import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import Index from "./pages/Index";
import Chat from "./pages/Chat";
import PapersList from "./pages/admin/Papers/PapersList";
import CreatePaper from "./pages/admin/Papers/CreatePaper";
import PaperDetail from "./pages/admin/Papers/PaperDetail";
import WorksheetsList from "./pages/admin/Worksheets/WorksheetsList";
import CreateWorksheet from "./pages/admin/Worksheets/CreateWorksheet";
import WorksheetDetail from "./pages/admin/Worksheets/WorksheetDetail";
import Demo from "./pages/Demo";
import NotFound from "./pages/NotFound";
import { widgetConfig } from "./config/widget.config";

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
            <Route path="/demo" element={<Demo />} />

            {/* Chat — enabled by feature flag */}
            {widgetConfig.features.chat && (
              <Route path="/chat" element={<Chat />} />
            )}

            {/* Question Paper Generator */}
            {widgetConfig.features.qpg && (
              <>
                <Route path="/question-paper" element={<PapersList />} />
                <Route path="/question-paper/new" element={<CreatePaper />} />
                <Route path="/question-paper/:id" element={<PaperDetail />} />
              </>
            )}

            {/* DPP / Daily Practice Problems */}
            {widgetConfig.features.dpp && (
              <>
                <Route path="/dpp" element={<WorksheetsList />} />
                <Route path="/dpp/new" element={<CreateWorksheet />} />
                <Route path="/dpp/:id" element={<WorksheetDetail />} />
              </>
            )}

            {/* Demo always accessible regardless of feature flags */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
