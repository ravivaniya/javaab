interface Props {
  chapters: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function ChapterSelector({ chapters, selected, onChange }: Props) {
  const allSelected = chapters.length > 0 && selected.length === chapters.length;

  const toggle = (ch: string) => {
    onChange(selected.includes(ch) ? selected.filter(s => s !== ch) : [...selected, ch]);
  };

  const toggleAll = () => {
    onChange(allSelected ? [] : [...chapters]);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Left — full chapter list */}
      <div className="bg-white rounded-2xl border border-black/10 p-4 max-h-72 overflow-y-auto">
        <label className="flex items-center gap-2 mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            className="accent-primary w-4 h-4"
          />
          <span className="text-sm font-bold text-[#1E1E1E]">Select All ({chapters.length})</span>
        </label>
        {chapters.map((ch, idx) => (
          <label key={ch} className="flex items-start gap-2 mb-2 cursor-pointer hover:bg-[#FAFAFA] rounded-lg px-1">
            <input
              type="checkbox"
              checked={selected.includes(ch)}
              onChange={() => toggle(ch)}
              className="accent-primary w-4 h-4 mt-0.5 shrink-0"
              data-testid={`chapter-${idx}`}
            />
            <span className="text-sm text-[#4B5563] leading-tight">{ch}</span>
          </label>
        ))}
        {chapters.length === 0 && (
          <p className="text-sm text-[#4B5563] italic">No chapters found. You can type chapter names below.</p>
        )}
      </div>

      {/* Right — selected preview */}
      <div className="bg-white rounded-2xl border border-black/10 p-4">
        <p className="text-sm font-bold text-[#1E1E1E] mb-3">Selected chapters ({selected.length})</p>
        {selected.length === 0 ? (
          <p className="text-sm text-[#4B5563] italic">No chapters selected yet</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selected.map(ch => (
              <span
                key={ch}
                className="inline-flex items-center gap-1 bg-primary/10 text-primary text-xs font-semibold px-3 py-1 rounded-full"
              >
                {ch.length > 30 ? ch.slice(0, 28) + "…" : ch}
                <button
                  type="button"
                  onClick={() => toggle(ch)}
                  className="hover:text-primary/80 ml-1 font-bold"
                  aria-label={`Remove ${ch}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
