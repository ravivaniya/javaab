import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Download, Printer, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { GeneratedWorksheet } from "@/types/worksheet";
import PaperPreview from "../Papers/components/PaperPreview";

export default function WorksheetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ws, setWs] = useState<GeneratedWorksheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  const fetchWs = useCallback(async () => {
    if (!id) return;
    try {
      const data = await ApiService.getWorksheet(id);
      setWs(data);
    } catch {
      toast.error("Failed to load worksheet");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchWs(); }, [fetchWs]);

  useEffect(() => {
    if (!ws || ws.status !== "generating") return;
    const timer = setInterval(fetchWs, 3000);
    return () => clearInterval(timer);
  }, [ws, fetchWs]);

  const handleDownload = async (type: string) => {
    setDownloading(type);
    try {
      await ApiService.downloadWorksheet(id!, type);
    } catch {
      toast.error("Download failed");
    } finally {
      setDownloading(null);
    }
  };

  const handlePrint = () => {
    if (!ws?.worksheet_html) return;
    const w = window.open("", "_blank");
    if (w) { w.document.write(ws.worksheet_html); w.document.close(); w.print(); }
  };

  const handleRegenerate = async () => {
    if (!ws) return;
    try {
      const res = await ApiService.generateWorksheet(ws.config);
      navigate(`/admin/worksheets/${res.worksheet_id}`);
    } catch {
      toast.error("Failed to start regeneration");
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="w-10 h-10 rounded-full border-4 border-[#FC8019] border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!ws) {
    return (
      <div className="p-8 text-center">
        <p className="text-[#4B5563]">Worksheet not found.</p>
        <Link to="/admin/worksheets" className="text-[#FC8019] font-bold mt-2 inline-block">← Back</Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row h-full min-h-screen">
      {/* Left panel */}
      <div className="lg:w-[40%] p-4 sm:p-6 border-b lg:border-b-0 lg:border-r border-black/5 space-y-5 overflow-y-auto">
        <Link to="/admin/worksheets" className="inline-flex items-center gap-2 text-sm text-[#4B5563] hover:text-[#FC8019] font-medium transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Worksheets
        </Link>

        <div>
          <h1 className="font-display font-black text-2xl text-[#1E1E1E]">{ws.topic}</h1>
          <p className="text-sm text-[#4B5563] mt-1">{ws.subject} · Class {ws.class_level} · {ws.board} · {ws.chapter}</p>
        </div>

        <div className="flex items-center gap-2">
          {ws.status === "generating" && (
            <span className="flex items-center gap-1.5 text-sm font-bold text-amber-600 bg-amber-50 px-4 py-2 rounded-full animate-pulse">
              ⚡ Generating…
            </span>
          )}
          {ws.status === "ready" && (
            <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-4 py-2 rounded-full">✅ Ready</span>
          )}
          {ws.status === "failed" && (
            <span className="text-sm font-bold text-rose-600 bg-rose-50 px-4 py-2 rounded-full">❌ Failed</span>
          )}
        </div>

        {ws.status === "ready" && (
          <div className="bg-white rounded-3xl border border-black/5 p-5 shadow-sm space-y-3">
            <h3 className="font-bold text-[#1E1E1E] text-sm">Downloads</h3>
            {[
              { type: "worksheet", label: "📄 Download Worksheet" },
              ...(ws.config?.include_answer_key ? [{ type: "answer_key", label: "🔑 Answer Key" }] : []),
            ].map(({ type, label }) => (
              <button
                key={type}
                onClick={() => handleDownload(type)}
                disabled={downloading === type}
                className="w-full flex items-center gap-2 bg-[#1E1E1E] text-white rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-black hover:-translate-y-0.5 transition-all disabled:opacity-60"
                data-testid={`download-${type}`}
              >
                {downloading === type ? <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" /> : <Download className="w-4 h-4" />}
                {label}
              </button>
            ))}
            <button
              onClick={handlePrint}
              className="w-full flex items-center gap-2 border-2 border-[#1E1E1E] rounded-full px-5 py-2.5 font-semibold text-sm hover:bg-[#1E1E1E] hover:text-white transition-all"
            >
              <Printer className="w-4 h-4" /> 🖨️ Print Preview
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            ["Questions", ws.num_questions],
            ["Type", ws.worksheet_type?.toUpperCase()],
            ["Difficulty", ws.config?.difficulty ?? "mixed"],
            ["Language", ws.config?.language?.toUpperCase() ?? "EN"],
          ].map(([label, val]) => (
            <div key={String(label)} className="bg-[#F3F4F6] rounded-2xl p-3">
              <p className="text-[#4B5563] text-xs capitalize">{label}</p>
              <p className="font-bold text-[#1E1E1E] capitalize">{val}</p>
            </div>
          ))}
        </div>

        <button
          onClick={handleRegenerate}
          className="flex items-center gap-2 border-2 border-black/20 rounded-full px-5 py-2.5 font-semibold text-sm text-[#4B5563] hover:border-[#FC8019] hover:text-[#FC8019] transition-all"
        >
          <RefreshCw className="w-4 h-4" /> ⟳ Regenerate
        </button>
      </div>

      {/* Right panel */}
      <div className="lg:flex-1 p-4 sm:p-6">
        <PaperPreview
          html={ws.worksheet_html ?? ""}
          isGenerating={ws.status === "generating"}
        />
      </div>
    </div>
  );
}
