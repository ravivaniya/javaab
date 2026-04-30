import type { DifficultyMix } from "@/types/paper";

interface Props {
  value: DifficultyMix;
  onChange: (v: DifficultyMix) => void;
}

export default function DifficultySlider({ value, onChange }: Props) {
  const handleChange = (key: keyof DifficultyMix, raw: number) => {
    const clamped = Math.max(0, Math.min(100, raw));
    const others = (["easy", "medium", "hard"] as (keyof DifficultyMix)[]).filter(k => k !== key);
    const remaining = 100 - clamped;
    const currentOtherTotal = value[others[0]] + value[others[1]];
    let o0 = currentOtherTotal === 0 ? Math.round(remaining / 2) : Math.round((value[others[0]] / currentOtherTotal) * remaining);
    let o1 = remaining - o0;
    if (o0 < 0) { o1 += o0; o0 = 0; }
    if (o1 < 0) { o0 += o1; o1 = 0; }
    onChange({ ...value, [key]: clamped, [others[0]]: o0, [others[1]]: o1 });
  };

  const segments: { key: keyof DifficultyMix; label: string; color: string; track: string }[] = [
    { key: "easy", label: "Easy", color: "text-emerald-600", track: "accent-emerald-500" },
    { key: "medium", label: "Medium", color: "text-amber-600", track: "accent-amber-500" },
    { key: "hard", label: "Hard", color: "text-rose-600", track: "accent-rose-500" },
  ];

  return (
    <div className="space-y-3">
      {segments.map(({ key, label, color, track }) => (
        <div key={key} className="flex items-center gap-3">
          <span className={`w-16 text-sm font-semibold ${color}`}>{label}</span>
          <input
            type="range"
            min={0}
            max={100}
            value={value[key]}
            onChange={e => handleChange(key, Number(e.target.value))}
            className={`flex-1 h-2 rounded-full ${track} cursor-pointer`}
            data-testid={`difficulty-${key}`}
          />
          <span className={`w-10 text-right text-sm font-bold ${color}`}>{value[key]}%</span>
        </div>
      ))}
      <p className="text-xs text-center text-[#4B5563] font-medium">
        {value.easy}% Easy · {value.medium}% Medium · {value.hard}% Hard
      </p>
    </div>
  );
}
