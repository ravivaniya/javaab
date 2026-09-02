import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Eye } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { GeneratedWorksheet, WorksheetType } from "@/types/worksheet";

const TYPE_LABELS: Record<WorksheetType, { label: string; color: string; emoji: string }> = {
  dpp: { label: "DPP", color: "bg-blue-100 text-blue-700", emoji: "📝" },
  worksheet: { label: "Worksheet", color: "bg-emerald-100 text-emerald-700", emoji: "📋" },
  revision: { label: "Revision", color: "bg-purple-100 text-purple-700", emoji: "🔄" },
  homework: { label: "Homework", color: "bg-amber-100 text-amber-700", emoji: "🏠" },
  mcq_drill: { label: "MCQ Drill", color: "bg-rose-100 text-rose-700", emoji: "🎯" },
};

const FILTERS: { label: string; value: WorksheetType | "all" }[] = [
  { label: "All", value: "all" },
  { label: "DPP", value: "dpp" },
  { label: "Worksheet", value: "worksheet" },
  { label: "Revision", value: "revision" },
  { label: "Homework", value: "homework" },
  { label: "MCQ Drill", value: "mcq_drill" },
];

export default function WorksheetsList() {
  const navigate = useNavigate();
  const [worksheets, setWorksheets] = useState<GeneratedWorksheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<WorksheetType | "all">("all");

  const fetchWorksheets = useCallback(async () => {
    try {
      const res = await ApiService.listWorksheets();
      setWorksheets(res.worksheets ?? []);
    } catch {
      toast.error("Failed to load worksheets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchWorksheets(); }, [fetchWorksheets]);

  useEffect(() => {
    const hasGenerating = worksheets.some(w => w.status === "generating");
    if (!hasGenerating) return;
    const id = setInterval(fetchWorksheets, 3000);
    return () => clearInterval(id);
  }, [worksheets, fetchWorksheets]);

  const handleDelete = async (wsId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await ApiService.deleteWorksheet(wsId);
      setWorksheets(prev => prev.filter(w => w.id !== wsId));
      toast.success("Worksheet deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const filtered = filter === "all" ? worksheets : worksheets.filter(w => w.worksheet_type === filter);

  return (
    <div className="p-4 sm:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-3xl text-[#1E1E1E] tracking-tight">DPPs & Worksheets</h1>
          <p className="text-[#4B5563] mt-1">Generate topic-focused practice sheets for your students.</p>
        </div>
        <button
          onClick={() => navigate("/dpp/new")}
          className="inline-flex items-center gap-2 bg-primary text-white rounded-full font-bold px-6 py-3 hover:opacity-90 hover:-translate-y-0.5 transition-all "
        >
          <Plus className="w-5 h-5" /> Create New
        </button>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${filter === f.value ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#4B5563] hover:bg-primary/10"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map(i => <div key={i} className="h-32 bg-white rounded-3xl border border-black/5 animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="text-6xl mb-4">📝</div>
          <h3 className="font-display font-black text-xl text-[#1E1E1E]">No worksheets yet</h3>
          <p className="text-[#4B5563] mt-2">Create a DPP or worksheet in under a minute</p>
          <button
            onClick={() => navigate("/dpp/new")}
            className="mt-6 inline-flex items-center gap-2 bg-primary text-white rounded-full font-bold px-8 py-4 hover:opacity-90 hover:-translate-y-1 transition-all "
          >
            <Plus className="w-5 h-5" /> Create New
          </button>
        </div>
      ) : (
        <AnimatePresence>
          <div className="grid gap-4">
            {filtered.map((ws, idx) => {
              const typeInfo = TYPE_LABELS[ws.worksheet_type] ?? TYPE_LABELS.dpp;
              return (
                <motion.div
                  key={ws.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all cursor-pointer"
                  onClick={() => navigate(`/dpp/${ws.id}`)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-xs font-bold px-3 py-1 rounded-full ${typeInfo.color}`}>
                          {typeInfo.emoji} {typeInfo.label}
                        </span>
                        <span className="text-xs text-[#4B5563] bg-[#F3F4F6] px-2 py-0.5 rounded-full">
                          {ws.subject} · Class {ws.class_level} · {ws.board}
                        </span>
                      </div>
                      <h3 className="font-display font-bold text-lg text-[#1E1E1E]">{ws.topic}</h3>
                      <p className="text-sm text-[#4B5563]">{ws.chapter} · {ws.num_questions} questions</p>
                      <p className="text-xs text-[#4B5563]">{formatDistanceToNow(new Date(ws.created_at), { addSuffix: true })}</p>
                    </div>
                    <div className="flex flex-col items-end gap-3">
                      {ws.status === "generating" && (
                        <span className="flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50 px-3 py-1 rounded-full animate-pulse">
                          ⚡ Generating…
                        </span>
                      )}
                      {ws.status === "ready" && (
                        <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">✅ Ready</span>
                      )}
                      {ws.status === "failed" && (
                        <span className="text-xs font-bold text-rose-600 bg-rose-50 px-3 py-1 rounded-full">❌ Failed</span>
                      )}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={e => { e.stopPropagation(); navigate(`/dpp/${ws.id}`); }}
                          className="flex items-center gap-1.5 border-2 border-[#1E1E1E] rounded-full px-4 py-2 text-sm font-bold hover:bg-[#1E1E1E] hover:text-white transition-all"
                        >
                          <Eye className="w-4 h-4" /> View
                        </button>
                        <button
                          onClick={e => handleDelete(ws.id, e)}
                          className="p-2 rounded-full border border-black/10 text-[#4B5563] hover:text-rose-500 hover:border-rose-200 transition-all"
                          aria-label="Delete worksheet"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </AnimatePresence>
      )}
    </div>
  );
}
