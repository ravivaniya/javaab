import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Download, Printer, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { GeneratedPaper } from "@/types/paper";
import PaperPreview from "./components/PaperPreview";

export default function PaperDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<GeneratedPaper | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeVariant, setActiveVariant] = useState(0);
  const [downloading, setDownloading] = useState<string | null>(null);

  const fetchPaper = useCallback(async () => {
    if (!id) return;
    try {
      const data = await ApiService.getPaper(id);
      setPaper(data);
    } catch {
      toast.error("Failed to load paper");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPaper();
  }, [fetchPaper]);

  // Poll while generating
  useEffect(() => {
    if (!paper || paper.status !== "generating") return;
    const timer = setInterval(fetchPaper, 3000);
    return () => clearInterval(timer);
  }, [paper, fetchPaper]);

  const handleDownload = async (variant: string, type: string) => {
    const key = `${variant}-${type}`;
    setDownloading(key);
    try {
      await ApiService.downloadPaper(id!, variant, type);
    } catch {
      toast.error("Download failed");
    } finally {
      setDownloading(null);
    }
  };

  const handlePrint = () => {
    if (!paper || !paper.variants[activeVariant]) return;
    const html = paper.variants[activeVariant].paper_html;
    const w = window.open("", "_blank");
    if (w) { w.document.write(html); w.document.close(); w.print(); }
  };

  const handleRegenerate = async () => {
    if (!paper) return;
    try {
      const res = await ApiService.generatePaper(paper.config);
      navigate(`/question-paper/${res.paper_id}`);
    } catch {
      toast.error("Failed to start regeneration");
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="w-10 h-10 rounded-full border-4 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="p-8 text-center">
        <p className="text-[#4B5563]">Paper not found.</p>
        <Link to="/question-paper" className="text-primary font-bold mt-2 inline-block">← Back to Papers</Link>
      </div>
    );
  }

  const variantLabels = paper.variants.length > 0
    ? paper.variants.map(v => v.variant_label)
    : ["Set A"];
  const currentVariant = paper.variants[activeVariant];
  const currentVariantLetter = variantLabels[activeVariant]?.replace("Set ", "") ?? "A";

  const questionCount = currentVariant
    ? Object.values(currentVariant.sections).reduce((acc, qs) => acc + qs.length, 0)
    : 0;

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-screen">
      {/* Left panel */}
      <div className="lg:w-[40%] p-4 sm:p-6 border-b lg:border-b-0 lg:border-r border-black/5 space-y-5 overflow-y-auto">
        <Link to="/question-paper" className="inline-flex items-center gap-2 text-sm text-[#4B5563] hover:text-primary font-medium transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Papers
        </Link>

        <div>
          <h1 className="font-display font-black text-2xl text-[#1E1E1E]">
            {paper.exam_title || "Question Paper"}
          </h1>
          <p className="text-sm text-[#4B5563] mt-1">
            Class {paper.class_level} · {paper.board} · {paper.subject}
          </p>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          {paper.status === "generating" && (
            <span className="flex items-center gap-1.5 text-sm font-bold text-amber-600 bg-amber-50 px-4 py-2 rounded-full animate-pulse">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
              ⚡ Generating…
            </span>
          )}
          {paper.status === "ready" && (
            <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-4 py-2 rounded-full">✅ Ready</span>
          )}
          {paper.status === "failed" && (
            <span className="text-sm font-bold text-rose-600 bg-rose-50 px-4 py-2 rounded-full">❌ Failed</span>
          )}
        </div>

        {/* Variant tabs */}
        {variantLabels.length > 1 && (
          <div className="flex gap-2">
            {variantLabels.map((label, i) => (
              <button
                key={label}
                onClick={() => setActiveVariant(i)}
                className={`px-4 py-2 rounded-full font-bold text-sm transition-all ${activeVariant === i ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-primary/10"}`}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Downloads */}
        {paper.status === "ready" && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-3xl border border-black/5 p-5 shadow-sm space-y-3"
          >
            <h3 className="font-bold text-[#1E1E1E] text-sm">Download ({variantLabels[activeVariant]})</h3>
            {[
              { type: "paper", label: "📄 Download Paper" },
              { type: "answer_key", label: "🔑 Answer Key" },
              { type: "marking_scheme", label: "📊 Marking Scheme" },
            ].map(({ type, label }) => {
              const key = `${currentVariantLetter}-${type}`;
              return (
                <button
                  key={type}
                  onClick={() => handleDownload(currentVariantLetter, type)}
                  disabled={downloading === key}
                  className="w-full flex items-center gap-2 bg-[#1E1E1E] text-white rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-black hover:-translate-y-0.5 transition-all disabled:opacity-60"
                  data-testid={`download-${type}-${currentVariantLetter}`}
                >
                  {downloading === key ? <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" /> : <Download className="w-4 h-4" />}
                  {label}
                </button>
              );
            })}
            <button
              onClick={handlePrint}
              className="w-full flex items-center gap-2 border-2 border-[#1E1E1E] rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-[#1E1E1E] hover:text-white transition-all"
            >
              <Printer className="w-4 h-4" /> 🖨️ Print Preview
            </button>
          </motion.div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            ["Questions", questionCount],
            ["Marks", paper.total_marks],
            ["Sections", paper.config?.sections?.length ?? "–"],
            ["Duration", `${paper.duration_minutes} min`],
          ].map(([label, val]) => (
            <div key={String(label)} className="bg-[#F3F4F6] rounded-2xl p-3">
              <p className="text-[#4B5563] text-xs">{label}</p>
              <p className="font-bold text-[#1E1E1E] text-lg">{val}</p>
            </div>
          ))}
        </div>

        {/* Actual generation stats — shown once paper is ready */}
        {paper.status === "ready" && paper.generation_stats && (
          <div className="rounded-2xl bg-[#F3F4F6] px-4 py-3 space-y-1.5 text-xs text-[#4B5563]">
            <p className="font-bold text-[#1E1E1E] text-sm mb-1">Generation Stats</p>
            <p>⏱ Time: <span className="font-semibold text-[#1E1E1E]">{paper.generation_stats.time_seconds}s</span></p>
            <p>🔢 Tokens: <span className="font-semibold text-[#1E1E1E]">{paper.generation_stats.total_tokens.toLocaleString()}</span>
              <span className="ml-1 opacity-70">({paper.generation_stats.prompt_tokens.toLocaleString()} in / {paper.generation_stats.completion_tokens.toLocaleString()} out)</span>
            </p>
            <p>🤖 Models: <span className="font-semibold text-[#1E1E1E]">{paper.generation_stats.models_used.join(", ")}</span></p>
          </div>
        )}

        <button
          onClick={handleRegenerate}
          className="flex items-center gap-2 border-2 border-black/20 rounded-full px-5 py-2.5 font-semibold text-sm text-[#4B5563] hover:border-primary hover:text-primary transition-all"
        >
          <RefreshCw className="w-4 h-4" /> ⟳ Regenerate
        </button>
      </div>

      {/* Right panel — preview */}
      <div className="lg:flex-1 p-4 sm:p-6">
        <PaperPreview
          html={currentVariant?.paper_html ?? ""}
          isGenerating={paper.status === "generating"}
        />
      </div>
    </div>
  );
}
