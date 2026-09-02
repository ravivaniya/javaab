import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { widgetConfig } from "@/config/widget.config";
import { Zap } from "lucide-react";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { WorksheetConfig, WorksheetType } from "@/types/worksheet";
import { getSubjects, getChapters, TOPIC_SUGGESTIONS } from "@/lib/chapters";

const INPUT_CLS = "w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all";

const WORKSHEET_TYPES: { value: WorksheetType; label: string; emoji: string; desc: string }[] = [
  { value: "dpp", label: "DPP", emoji: "📝", desc: "Daily Practice" },
  { value: "worksheet", label: "Worksheet", emoji: "📋", desc: "Concept practice" },
  { value: "revision", label: "Revision", emoji: "🔄", desc: "Before test" },
  { value: "homework", label: "Homework", emoji: "🏠", desc: "Take-home" },
  { value: "mcq_drill", label: "MCQ Drill", emoji: "🎯", desc: "Pure MCQ" },
];

const DIFFICULTIES = ["easy", "medium", "hard", "mixed"] as const;

export default function CreateWorksheet() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [board, setBoard] = useState<"CBSE" | "GSEB">("CBSE");
  const [classLevel, setClassLevel] = useState(10);
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [topic, setTopic] = useState("");
  const [showTopicSuggestions, setShowTopicSuggestions] = useState(false);
  const [worksheetType, setWorksheetType] = useState<WorksheetType>("dpp");
  const [numQuestions, setNumQuestions] = useState(15);
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard" | "mixed">("mixed");
  const [includeTheory, setIncludeTheory] = useState(true);
  const [includeHints, setIncludeHints] = useState(false);
  const [includeAnswerKey, setIncludeAnswerKey] = useState(true);
  const [dateField, setDateField] = useState(true);
  const [studentNameField, setStudentNameField] = useState(true);
  const [language, setLanguage] = useState("en");
  const [instituteName, setInstituteName] = useState(widgetConfig.institute.name);

  const availableSubjects = getSubjects(board, classLevel);
  const availableChapters = subject ? getChapters(board, classLevel, subject) : [];

  const topicSuggestions = useMemo(() => {
    const suggestions = TOPIC_SUGGESTIONS[subject] ?? [];
    if (!topic) return suggestions.slice(0, 6);
    return suggestions.filter(t => t.toLowerCase().includes(topic.toLowerCase())).slice(0, 6);
  }, [subject, topic]);

  const estimatedMinutes = Math.round(numQuestions * 1.5);

  const handleGenerate = async () => {
    if (!subject) { toast.error("Select a subject"); return; }
    if (!chapter) { toast.error("Select a chapter"); return; }
    if (!topic.trim()) { toast.error("Enter a topic"); return; }

    const config: WorksheetConfig = {
      board, class_level: classLevel, subject, topic, chapter,
      worksheet_type: worksheetType, num_questions: numQuestions,
      difficulty, include_theory_summary: includeTheory,
      include_hints: includeHints, include_answer_key: includeAnswerKey,
      language, institute_name: instituteName,
      date_field: dateField, student_name_field: studentNameField,
    };

    setSubmitting(true);
    try {
      const res = await ApiService.generateWorksheet(config);
      navigate(`/dpp/${res.worksheet_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Generation failed");
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display font-black text-2xl text-[#1E1E1E]">Create DPP / Worksheet</h1>
        <p className="text-[#4B5563] mt-1">Fill in the details and generate in ~20–30 seconds.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT COLUMN */}
        <div className="space-y-6">
          {/* Section 1: What to practice */}
          <div className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm space-y-4">
            <h2 className="font-bold text-[#1E1E1E]">📚 What to practice?</h2>

            {/* Board */}
            <div className="flex gap-2">
              {(["CBSE", "GSEB"] as const).map(b => (
                <button
                  key={b}
                  type="button"
                  onClick={() => { setBoard(b); setSubject(""); setChapter(""); }}
                  className={`flex-1 py-2 px-4 rounded-full font-bold text-sm transition-all ${board === b ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-primary/10"}`}
                >
                  {b}
                </button>
              ))}
            </div>

            {/* Class */}
            <div className="flex flex-wrap gap-2">
              {[6, 7, 8, 9, 10, 11, 12].map(n => (
                <button
                  key={n}
                  type="button"
                  onClick={() => { setClassLevel(n); setSubject(""); setChapter(""); }}
                  className={`w-9 h-9 rounded-full font-bold text-sm transition-all ${classLevel === n ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-primary/10"}`}
                >
                  {n}
                </button>
              ))}
            </div>

            {/* Subject */}
            <select
              value={subject}
              onChange={e => { setSubject(e.target.value); setChapter(""); }}
              className={INPUT_CLS}
            >
              <option value="">Select subject…</option>
              {availableSubjects.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            {/* Chapter */}
            {availableChapters.length > 0 ? (
              <select
                value={chapter}
                onChange={e => setChapter(e.target.value)}
                className={INPUT_CLS}
              >
                <option value="">Select chapter…</option>
                {availableChapters.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            ) : (
              <input
                type="text"
                value={chapter}
                onChange={e => setChapter(e.target.value)}
                placeholder="Enter chapter name…"
                className={INPUT_CLS}
              />
            )}

            {/* Topic with autocomplete */}
            <div className="relative">
              <input
                type="text"
                value={topic}
                onChange={e => setTopic(e.target.value)}
                onFocus={() => setShowTopicSuggestions(true)}
                onBlur={() => setTimeout(() => setShowTopicSuggestions(false), 150)}
                placeholder="Topic: Quadratic Equations, Photosynthesis…"
                className={INPUT_CLS}
                data-testid="topic-input"
              />
              {showTopicSuggestions && topicSuggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-2xl border border-black/10 shadow-lg z-10 overflow-hidden">
                  {topicSuggestions.map(s => (
                    <button
                      key={s}
                      type="button"
                      onMouseDown={() => setTopic(s)}
                      className="w-full text-left px-4 py-2.5 text-sm text-[#1E1E1E] hover:bg-primary/5 hover:text-primary transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Section 2: Worksheet type */}
          <div className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm space-y-3">
            <h2 className="font-bold text-[#1E1E1E]">📄 Worksheet Type</h2>
            <div className="grid grid-cols-2 gap-3">
              {WORKSHEET_TYPES.map(t => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setWorksheetType(t.value)}
                  className={`rounded-2xl border-2 p-3 text-left transition-all ${worksheetType === t.value ? "border-primary bg-primary/5" : "border-black/10 hover:border-black/30"}`}
                  data-testid={`type-${t.value}`}
                >
                  <div className="text-xl">{t.emoji}</div>
                  <div className="font-bold text-sm mt-1">{t.label}</div>
                  <div className="text-xs text-[#4B5563]">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Section 3: Settings */}
          <div className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm space-y-4">
            <h2 className="font-bold text-[#1E1E1E]">⚙️ Settings</h2>

            <div>
              <div className="flex justify-between text-sm font-medium text-[#1E1E1E] mb-2">
                <span>Questions</span>
                <span className="font-bold text-primary">{numQuestions}</span>
              </div>
              <input
                type="range"
                min={5}
                max={30}
                value={numQuestions}
                onChange={e => setNumQuestions(Number(e.target.value))}
                className="w-full accent-primary cursor-pointer"
                data-testid="num-questions-slider"
              />
              <div className="flex justify-between text-xs text-[#4B5563] mt-1">
                <span>5</span><span>30</span>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium text-[#1E1E1E] mb-2">Difficulty</p>
              <div className="flex gap-2">
                {DIFFICULTIES.map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDifficulty(d)}
                    className={`flex-1 py-2 rounded-full text-xs font-bold transition-all capitalize ${difficulty === d ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-primary/10"}`}
                    data-testid={`difficulty-${d}`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              {[
                { label: "Include theory summary", val: includeTheory, set: setIncludeTheory, testId: "toggle-theory" },
                { label: "Include hints", val: includeHints, set: setIncludeHints, testId: "toggle-hints" },
                { label: "Include answer key", val: includeAnswerKey, set: setIncludeAnswerKey, testId: "toggle-answer-key" },
                { label: "Date field for student", val: dateField, set: setDateField, testId: "toggle-date" },
                { label: "Student name field", val: studentNameField, set: setStudentNameField, testId: "toggle-name" },
              ].map(({ label, val, set, testId }) => (
                <label key={label} className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm text-[#1E1E1E]">{label}</span>
                  <div
                    onClick={() => set(!val)}
                    className={`relative w-10 h-5 rounded-full transition-all cursor-pointer ${val ? "bg-primary" : "bg-[#D1D5DB]"}`}
                    data-testid={testId}
                  >
                    <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${val ? "translate-x-5" : "translate-x-0.5"}`} />
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-2">
              {[["en", "English"], ["hi", "हिन्दी"], ["gu", "ગુજ"]].map(([code, label]) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLanguage(code)}
                  className={`flex-1 py-2 rounded-full text-xs font-bold transition-all ${language === code ? "bg-primary text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-primary/10"}`}
                >
                  {label}
                </button>
              ))}
            </div>

            <input
              type="text"
              value={instituteName}
              onChange={e => setInstituteName(e.target.value)}
              placeholder="Institute name (optional)"
              className={INPUT_CLS}
            />
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="lg:sticky lg:top-6 space-y-4 self-start">
          <div className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm">
            <h2 className="font-bold text-[#1E1E1E] mb-4">Your worksheet will have:</h2>
            <div className="text-center mb-6">
              <div className="text-6xl font-black text-primary">{numQuestions}</div>
              <div className="text-[#4B5563] font-medium">Questions</div>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-[#4B5563]">Est. time for students</span>
                <span className="font-bold text-[#1E1E1E]">~{estimatedMinutes} min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#4B5563]">Type</span>
                <span className={`font-bold px-2 py-0.5 rounded-full text-xs ${WORKSHEET_TYPES.find(t => t.value === worksheetType)?.label ? "bg-primary/10 text-primary" : ""}`}>
                  {WORKSHEET_TYPES.find(t => t.value === worksheetType)?.label}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#4B5563]">Difficulty</span>
                <span className="font-bold text-[#1E1E1E] capitalize">{difficulty}</span>
              </div>
              {subject && <div className="flex justify-between">
                <span className="text-[#4B5563]">Subject</span>
                <span className="font-bold text-[#1E1E1E]">{subject}</span>
              </div>}
              {topic && <div className="flex justify-between">
                <span className="text-[#4B5563]">Topic</span>
                <span className="font-bold text-[#1E1E1E] text-right max-w-[160px] truncate">{topic}</span>
              </div>}
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 bg-primary text-white rounded-full font-bold py-4 text-lg hover:opacity-90 hover:-translate-y-0.5 transition-all  disabled:opacity-60 disabled:cursor-not-allowed"
            data-testid="generate-worksheet-btn"
          >
            {submitting ? (
              <span className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
            ) : (
              <Zap className="w-5 h-5" />
            )}
            {submitting ? "Submitting…" : "⚡ Generate Now"}
          </button>
          <p className="text-center text-xs text-[#4B5563]">~20–30 seconds</p>
        </div>
      </div>
    </div>
  );
}
