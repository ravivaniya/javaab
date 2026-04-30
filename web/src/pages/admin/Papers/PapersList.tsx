import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Eye, FileText } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { GeneratedPaper } from "@/types/paper";

const SUBJECT_COLORS: Record<string, string> = {
  Mathematics: "bg-blue-100 text-blue-700",
  Science: "bg-emerald-100 text-emerald-700",
  Physics: "bg-purple-100 text-purple-700",
  Chemistry: "bg-amber-100 text-amber-700",
  Biology: "bg-green-100 text-green-700",
  "Social Science": "bg-orange-100 text-orange-700",
};

export default function PapersList() {
  const navigate = useNavigate();
  const [papers, setPapers] = useState<GeneratedPaper[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPapers = useCallback(async () => {
    try {
      const res = await ApiService.listPapers();
      setPapers(res.papers ?? []);
    } catch {
      toast.error("Failed to load papers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  // Poll while any paper is generating
  useEffect(() => {
    const hasGenerating = papers.some(p => p.status === "generating");
    if (!hasGenerating) return;
    const id = setInterval(fetchPapers, 3000);
    return () => clearInterval(id);
  }, [papers, fetchPapers]);

  const handleDelete = async (paperId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await ApiService.deletePaper(paperId);
      setPapers(prev => prev.filter(p => p.id !== paperId));
      toast.success("Paper deleted");
    } catch {
      toast.error("Failed to delete paper");
    }
  };

  const totalSets = papers.reduce((acc, p) => acc + (p.num_variants ?? 1), 0);

  return (
    <div className="p-4 sm:p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-3xl text-[#1E1E1E] tracking-tight">Question Papers</h1>
          <p className="text-[#4B5563] mt-1">Generate AI-powered exam papers for your class.</p>
        </div>
        <button
          onClick={() => navigate("/admin/teacher/papers/new")}
          className="inline-flex items-center gap-2 bg-[#FC8019] text-white rounded-full font-bold px-6 py-3 hover:bg-[#E67315] hover:-translate-y-0.5 transition-all shadow-[0_8px_32px_rgba(252,128,25,0.15)]"
          data-testid="create-paper-btn"
        >
          <Plus className="w-5 h-5" /> Create New Paper
        </button>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Papers Generated", value: papers.length },
          { label: "Total Sets Created", value: totalSets },
          { label: "Ready to Download", value: papers.filter(p => p.status === "ready").length },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm">
            <p className="text-sm text-[#4B5563] font-medium">{stat.label}</p>
            <p className="text-3xl font-black text-[#1E1E1E] mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Papers list */}
      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-40 bg-white rounded-3xl border border-black/5 animate-pulse" />
          ))}
        </div>
      ) : papers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <svg width="120" height="120" viewBox="0 0 120 120" fill="none" className="mb-6 opacity-30">
            <rect x="20" y="10" width="80" height="100" rx="8" fill="#FC8019" />
            <rect x="30" y="30" width="60" height="4" rx="2" fill="white" />
            <rect x="30" y="42" width="50" height="4" rx="2" fill="white" />
            <rect x="30" y="54" width="55" height="4" rx="2" fill="white" />
            <rect x="30" y="66" width="40" height="4" rx="2" fill="white" />
            <circle cx="88" cy="88" r="22" fill="#1E1E1E" />
            <path d="M80 88l6 6 12-12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <h3 className="font-display font-black text-xl text-[#1E1E1E]">No question papers yet</h3>
          <p className="text-[#4B5563] mt-2">Create your first paper in under 2 minutes</p>
          <button
            onClick={() => navigate("/admin/teacher/papers/new")}
            className="mt-6 inline-flex items-center gap-2 bg-[#FC8019] text-white rounded-full font-bold px-8 py-4 hover:bg-[#E67315] hover:-translate-y-1 transition-all shadow-[0_8px_32px_rgba(252,128,25,0.15)]"
          >
            <Plus className="w-5 h-5" /> Create New Paper
          </button>
        </div>
      ) : (
        <AnimatePresence>
          <div className="grid gap-4">
            {papers.map((paper, idx) => {
              const subjectColor = SUBJECT_COLORS[paper.subject] ?? "bg-gray-100 text-gray-700";
              const isGenerating = paper.status === "generating";
              const isFailed = paper.status === "failed";
              return (
                <motion.div
                  key={paper.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all cursor-pointer"
                  onClick={() => navigate(`/admin/teacher/papers/${paper.id}`)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-xs font-bold px-3 py-1 rounded-full ${subjectColor}`}>
                          {paper.subject}
                        </span>
                        <span className="text-xs text-[#4B5563] bg-[#F3F4F6] px-2 py-0.5 rounded-full">
                          Class {paper.class_level} · {paper.board}
                        </span>
                        {(paper.num_variants ?? 1) > 1 && (
                          <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full">
                            {paper.num_variants} Sets
                          </span>
                        )}
                      </div>
                      <h3 className="font-display font-bold text-lg text-[#1E1E1E]">
                        {paper.exam_title || "Untitled Paper"}
                      </h3>
                      <p className="text-sm text-[#4B5563]">
                        {paper.total_marks} marks · {paper.duration_minutes} min
                        {paper.chapters_count ? ` · ${paper.chapters_count} chapter${paper.chapters_count !== 1 ? "s" : ""}` : ""}
                      </p>
                      <p className="text-xs text-[#4B5563]">
                        {formatDistanceToNow(new Date(paper.created_at), { addSuffix: true })}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-3">
                      {isGenerating && (
                        <span className="flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50 px-3 py-1 rounded-full animate-pulse">
                          <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                          ⚡ Generating…
                        </span>
                      )}
                      {paper.status === "ready" && (
                        <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
                          ✅ Ready
                        </span>
                      )}
                      {isFailed && (
                        <span className="text-xs font-bold text-rose-600 bg-rose-50 px-3 py-1 rounded-full">
                          ❌ Failed
                        </span>
                      )}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={e => { e.stopPropagation(); navigate(`/admin/teacher/papers/${paper.id}`); }}
                          className="flex items-center gap-1.5 border-2 border-[#1E1E1E] rounded-full px-4 py-2 text-sm font-bold hover:bg-[#1E1E1E] hover:text-white transition-all"
                        >
                          <Eye className="w-4 h-4" /> View
                        </button>
                        <button
                          onClick={e => handleDelete(paper.id, e)}
                          className="p-2 rounded-full border border-black/10 text-[#4B5563] hover:text-rose-500 hover:border-rose-200 transition-all"
                          aria-label="Delete paper"
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
