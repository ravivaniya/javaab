import { useState } from "react";
import { ZoomIn, ZoomOut } from "lucide-react";

interface Props {
  html: string;
  isGenerating?: boolean;
}

const ZOOM_LEVELS = [75, 100, 125];

export default function PaperPreview({ html, isGenerating = false }: Props) {
  const [zoomIdx, setZoomIdx] = useState(1);
  const zoom = ZOOM_LEVELS[zoomIdx];

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] bg-white rounded-3xl border border-black/5">
        <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin mb-4" />
        <p className="text-primary font-bold text-lg">⚡ Generating your paper…</p>
        <p className="text-[#4B5563] text-sm mt-1">This may take 30–60 seconds</p>
        <div className="mt-6 space-y-2 w-64">
          {[80, 60, 90, 50].map((w, i) => (
            <div key={i} className="h-3 bg-[#F3F4F6] rounded-full animate-pulse" style={{ width: `${w}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!html) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px] bg-white rounded-3xl border border-black/5">
        <p className="text-[#4B5563]">No preview available</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-[400px] bg-[#F3F4F6] rounded-3xl overflow-hidden border border-black/5">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-black/5">
        <span className="text-sm font-medium text-[#4B5563]">Preview</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoomIdx(i => Math.max(0, i - 1))}
            disabled={zoomIdx === 0}
            className="p-1.5 rounded-lg hover:bg-[#F3F4F6] disabled:opacity-40"
          >
            <ZoomOut className="w-4 h-4 text-[#4B5563]" />
          </button>
          <span className="text-sm font-semibold text-[#1E1E1E] w-10 text-center">{zoom}%</span>
          <button
            onClick={() => setZoomIdx(i => Math.min(ZOOM_LEVELS.length - 1, i + 1))}
            disabled={zoomIdx === ZOOM_LEVELS.length - 1}
            className="p-1.5 rounded-lg hover:bg-[#F3F4F6] disabled:opacity-40"
          >
            <ZoomIn className="w-4 h-4 text-[#4B5563]" />
          </button>
        </div>
      </div>
      {/* iframe */}
      <div className="flex-1 overflow-auto p-4">
        <div
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top left", width: `${10000 / zoom}%` }}
        >
          <iframe
            srcDoc={html}
            title="Paper Preview"
            className="w-full border-0 bg-white shadow-lg"
            style={{ minHeight: "1000px" }}
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      </div>
    </div>
  );
}
