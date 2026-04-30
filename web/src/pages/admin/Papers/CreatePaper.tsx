import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, ChevronLeft, Zap, Upload, X } from "lucide-react";
import { toast } from "sonner";
import { ApiService } from "@/services/api";
import type { PaperConfig, SectionConfig, DifficultyMix } from "@/types/paper";
import { getSubjects, getChapters } from "@/lib/chapters";
import ChapterSelector from "./components/ChapterSelector";
import DifficultySlider from "./components/DifficultySlider";
import SectionBuilder from "./components/SectionBuilder";

const STEPS = ["Basics", "Chapters", "Sections", "Settings"];

const CBSE_10_STANDARD: SectionConfig[] = [
  { section_label: "Section A", question_type: "mcq", num_questions: 20, marks_per_question: 1, instructions: "" },
  { section_label: "Section B", question_type: "short", num_questions: 6, marks_per_question: 2, instructions: "" },
  { section_label: "Section C", question_type: "short", num_questions: 7, marks_per_question: 3, instructions: "" },
  { section_label: "Section D", question_type: "long", num_questions: 3, marks_per_question: 5, instructions: "" },
];

const UNIT_TEST: SectionConfig[] = [
  { section_label: "Section A", question_type: "mcq", num_questions: 10, marks_per_question: 1, instructions: "" },
  { section_label: "Section B", question_type: "short", num_questions: 5, marks_per_question: 2, instructions: "" },
  { section_label: "Section C", question_type: "long", num_questions: 2, marks_per_question: 5, instructions: "" },
];

const CBSE_12_STANDARD: SectionConfig[] = [
  { section_label: "Section A", question_type: "mcq", num_questions: 16, marks_per_question: 1, instructions: "" },
  { section_label: "Section B", question_type: "assertion_reason", num_questions: 4, marks_per_question: 1, instructions: "" },
  { section_label: "Section C", question_type: "short", num_questions: 5, marks_per_question: 2, instructions: "" },
  { section_label: "Section D", question_type: "short", num_questions: 4, marks_per_question: 3, instructions: "" },
  { section_label: "Section E", question_type: "long", num_questions: 3, marks_per_question: 5, instructions: "" },
];

const INSTRUCTION_PRESETS = [
  {
    label: "CBSE Standard",
    text: "1. All questions are compulsory unless stated otherwise.\n2. Write your name and roll number clearly.\n3. Marks are indicated against each question.\n4. Draw neat, labelled diagrams wherever necessary.\n5. Use of calculator is not permitted.",
  },
  {
    label: "Gujarat Board",
    text: "1. Write your seat number at the top.\n2. All questions carry marks as indicated.\n3. Draw diagrams where necessary.\n4. Start each section on a new page.\n5. Maintain neat and clean presentation.",
  },
  {
    label: "Unit Test",
    text: "1. All questions are compulsory.\n2. Marks are given against each question.\n3. Write answers in neat handwriting.",
  },
];

const LS_INSTITUTE = "javaab:institute_name";

const INPUT_CLS = "w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-[#FC8019] focus:ring-2 focus:ring-[#FC8019]/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all";

export default function CreatePaper() {
  const navigate = useNavigate();
  const logoInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [board, setBoard] = useState<"CBSE" | "GSEB">("CBSE");
  const [classLevel, setClassLevel] = useState<number>(10);
  const [subject, setSubject] = useState("");
  const [examTitle, setExamTitle] = useState("");
  const [duration, setDuration] = useState(180);
  const [totalMarks, setTotalMarks] = useState(80);
  const [language, setLanguage] = useState("en");
  const [variants, setVariants] = useState(1);

  const [chapters, setChapters] = useState<string[]>([]);
  const [customChapters, setCustomChapters] = useState("");
  const [difficultyMix, setDifficultyMix] = useState<DifficultyMix>({ easy: 30, medium: 50, hard: 20 });

  const [sections, setSections] = useState<SectionConfig[]>(CBSE_10_STANDARD);

  const [instituteName, setInstituteName] = useState("");
  const [instituteLogoUrl, setInstituteLogoUrl] = useState("");
  const [paperInstructions, setPaperInstructions] = useState("");
  const [includeAnswerKey, setIncludeAnswerKey] = useState(true);
  const [includeMarkingScheme, setIncludeMarkingScheme] = useState(true);

  // Load saved institute name from localStorage on first render
  useEffect(() => {
    const saved = localStorage.getItem(LS_INSTITUTE);
    if (saved) setInstituteName(saved);
  }, []);

  const handleInstituteNameChange = (value: string) => {
    setInstituteName(value);
    localStorage.setItem(LS_INSTITUTE, value);
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 500_000) { toast.error("Logo must be under 500 KB"); return; }
    const reader = new FileReader();
    reader.onload = (ev) => setInstituteLogoUrl(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const availableSubjects = getSubjects(board, classLevel);
  const availableChapters = subject ? getChapters(board, classLevel, subject) : [];
  const computedTotal = sections.reduce((acc, s) => acc + s.num_questions * s.marks_per_question, 0);
  const estimatedTokens = sections.reduce((acc, s) => acc + s.num_questions * 200, 0);
  const estimatedSec = Math.max(30, Math.round(sections.length * 15 + sections.reduce((a, s) => a + s.num_questions, 0) * 2));

  const validateStep = () => {
    if (step === 1) {
      if (!board) return "Select a board";
      if (!classLevel) return "Select a class";
      if (!subject) return "Select a subject";
      if (!examTitle.trim()) return "Enter exam title";
      if (duration < 10) return "Duration must be at least 10 minutes";
      if (totalMarks < 1) return "Total marks must be at least 1";
    }
    if (step === 2) {
      const effective = availableChapters.length > 0 ? chapters : customChapters.split("\n").filter(Boolean);
      if (effective.length === 0) return "Select at least one chapter";
    }
    if (step === 3) {
      if (sections.length === 0) return "Add at least one section";
    }
    return null;
  };

  const next = () => {
    const err = validateStep();
    if (err) { toast.error(err); return; }
    setStep(s => Math.min(4, s + 1));
  };

  const back = () => setStep(s => Math.max(1, s - 1));

  const handleGenerate = async () => {
    const effectiveChapters = availableChapters.length > 0
      ? chapters
      : customChapters.split("\n").map(c => c.trim()).filter(Boolean);

    const config: PaperConfig = {
      board, class_level: classLevel, subject,
      chapters: effectiveChapters,
      difficulty_mix: difficultyMix,
      sections,
      total_marks: totalMarks,
      duration_minutes: duration,
      num_variants: variants,
      include_answer_key: includeAnswerKey,
      include_marking_scheme: includeMarkingScheme,
      language, exam_title: examTitle,
      institute_name: instituteName,
      institute_logo_url: instituteLogoUrl,
      paper_instructions: paperInstructions,
    };

    setSubmitting(true);
    try {
      const res = await ApiService.generatePaper(config);
      navigate(`/admin/teacher/papers/${res.paper_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Generation failed");
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto space-y-6">
      {/* Progress bar */}
      <div>
        <h1 className="font-display font-black text-2xl text-[#1E1E1E] mb-4">Create Question Paper</h1>
        <div className="flex items-center gap-1">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const done = step > n;
            const current = step === n;
            return (
              <div key={label} className="flex items-center flex-1 last:flex-none">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 font-bold text-sm transition-all
                  ${done ? "bg-[#FC8019] border-[#FC8019] text-white" : current ? "border-[#FC8019] text-[#FC8019]" : "border-black/20 text-[#4B5563]"}`}>
                  {done ? "✓" : n}
                </div>
                <span className={`ml-2 text-sm font-medium hidden sm:block ${current ? "text-[#FC8019]" : "text-[#4B5563]"}`}>{label}</span>
                {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 mx-3 ${done ? "bg-[#FC8019]" : "bg-black/10"}`} />}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          transition={{ duration: 0.2 }}
        >
          {/* STEP 1 */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-5">
                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Board</label>
                    <div className="grid grid-cols-2 gap-3">
                      {(["CBSE", "GSEB"] as const).map(b => (
                        <button key={b} type="button"
                          onClick={() => { setBoard(b); setSubject(""); setChapters([]); }}
                          className={`rounded-2xl border-2 p-4 text-left transition-all ${board === b ? "border-[#FC8019] bg-[#FC8019]/5 text-[#FC8019]" : "border-black/10 text-[#1E1E1E] hover:border-black/30"}`}>
                          <div className="font-bold">{b}</div>
                          <div className="text-xs mt-0.5 opacity-70">{b === "CBSE" ? "NCERT syllabus" : "Gujarat Board"}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Class</label>
                    <div className="flex flex-wrap gap-2">
                      {[6, 7, 8, 9, 10, 11, 12].map(n => (
                        <button key={n} type="button"
                          onClick={() => { setClassLevel(n); setSubject(""); setChapters([]); }}
                          className={`w-10 h-10 rounded-full font-bold text-sm transition-all ${classLevel === n ? "bg-[#FC8019] text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-[#FC8019]/10"}`}>
                          {n}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Subject</label>
                    <select value={subject} onChange={e => { setSubject(e.target.value); setChapters([]); }} className={INPUT_CLS}>
                      <option value="">Select subject…</option>
                      {availableSubjects.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Exam Title</label>
                    <input type="text" value={examTitle} onChange={e => setExamTitle(e.target.value)}
                      placeholder="Unit Test 1, Half Yearly Exam…" className={INPUT_CLS} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Duration (min)</label>
                      <input type="number" min={10} value={duration} onChange={e => setDuration(Number(e.target.value))} className={INPUT_CLS} />
                    </div>
                    <div>
                      <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Total Marks</label>
                      <input type="number" min={1} value={totalMarks} onChange={e => setTotalMarks(Number(e.target.value))} className={INPUT_CLS} />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Language</label>
                    <div className="flex gap-2">
                      {[["en", "English"], ["hi", "हिन्दी"], ["gu", "ગુજરાતી"]].map(([code, label]) => (
                        <button key={code} type="button" onClick={() => setLanguage(code)}
                          className={`flex-1 py-2 px-3 rounded-full font-medium text-sm transition-all ${language === code ? "bg-[#FC8019] text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-[#FC8019]/10"}`}>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Number of Sets</label>
                    <div className="flex gap-2">
                      {([[1, "1 Set"], [2, "2 Sets (A, B)"], [3, "3 Sets (A, B, C)"]] as [number, string][]).map(([n, label]) => (
                        <button key={n} type="button" onClick={() => setVariants(n)}
                          className={`flex-1 py-2 px-3 rounded-full font-medium text-xs transition-all ${variants === n ? "bg-[#FC8019] text-white" : "bg-[#F3F4F6] text-[#1E1E1E] hover:bg-[#FC8019]/10"}`}>
                          {label}
                        </button>
                      ))}
                    </div>
                    {variants > 1 && (
                      <p className="text-xs text-[#4B5563] mt-2 bg-[#F3F4F6] rounded-xl px-3 py-2">
                        ℹ Questions are generated once and shuffled per set — same content, different order.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div className="space-y-6">
              <h2 className="font-display font-bold text-lg text-[#1E1E1E]">Choose Chapters</h2>
              {availableChapters.length > 0 ? (
                <ChapterSelector chapters={availableChapters} selected={chapters} onChange={setChapters} />
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-amber-600 bg-amber-50 px-4 py-2 rounded-2xl">
                    ⚠ Chapter list not available for this combination. Enter chapter names below (one per line).
                  </p>
                  <textarea rows={6} value={customChapters} onChange={e => setCustomChapters(e.target.value)}
                    placeholder={"Chapter 1: Chemical Reactions\nChapter 2: Acids and Bases\nChapter 3: Metals and Non-metals"}
                    className={INPUT_CLS} />
                </div>
              )}
              <div>
                <h3 className="font-bold text-sm text-[#1E1E1E] mb-3">Difficulty Mix</h3>
                <DifficultySlider value={difficultyMix} onChange={setDifficultyMix} />
              </div>
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="font-display font-bold text-lg text-[#1E1E1E] mb-2">Build Sections</h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {[
                    { label: "CBSE Class 10", sections: CBSE_10_STANDARD },
                    { label: "CBSE Class 12", sections: CBSE_12_STANDARD },
                    { label: "Unit Test", sections: UNIT_TEST },
                    { label: "Custom (Empty)", sections: [] },
                  ].map(preset => (
                    <button key={preset.label} type="button" onClick={() => setSections(preset.sections)}
                      className="px-4 py-2 text-sm font-semibold rounded-full border-2 border-[#1E1E1E] hover:bg-[#1E1E1E] hover:text-white transition-all">
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
              <SectionBuilder sections={sections} onChange={setSections} targetMarks={totalMarks} />
            </div>
          )}

          {/* STEP 4 */}
          {step === 4 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left */}
              <div className="space-y-4">
                <h2 className="font-display font-bold text-lg text-[#1E1E1E]">Final Settings</h2>

                {/* Institute name — saved automatically */}
                <div>
                  <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Institute Name</label>
                  <input type="text" value={instituteName}
                    onChange={e => handleInstituteNameChange(e.target.value)}
                    placeholder="Brilliant Academy"
                    className={INPUT_CLS} />
                  {instituteName && (
                    <p className="text-xs text-emerald-600 mt-1">✓ Saved for next time</p>
                  )}
                </div>

                {/* Logo upload */}
                <div>
                  <label className="text-sm font-bold text-[#1E1E1E] mb-2 block">Institute Logo</label>
                  <input ref={logoInputRef} type="file" accept="image/*" className="hidden" onChange={handleLogoUpload} />
                  {instituteLogoUrl ? (
                    <div className="flex items-center gap-3">
                      <img src={instituteLogoUrl} alt="Logo preview" className="h-14 object-contain rounded-xl border border-black/10 px-2 py-1 bg-white" />
                      <button
                        type="button"
                        onClick={() => { setInstituteLogoUrl(""); if (logoInputRef.current) logoInputRef.current.value = ""; }}
                        className="flex items-center gap-1.5 text-sm text-rose-500 hover:text-rose-600 font-medium"
                      >
                        <X className="w-4 h-4" /> Remove
                      </button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => logoInputRef.current?.click()}
                      className="flex items-center gap-2 w-full rounded-2xl border-2 border-dashed border-black/15 px-4 py-4 text-sm font-medium text-[#4B5563] hover:border-[#FC8019] hover:text-[#FC8019] transition-all">
                      <Upload className="w-4 h-4" />
                      Upload logo (PNG / JPG, max 500 KB)
                    </button>
                  )}
                </div>

                {/* Instructions with presets */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-bold text-[#1E1E1E]">Paper Instructions</label>
                    <div className="flex gap-1">
                      {INSTRUCTION_PRESETS.map(p => (
                        <button key={p.label} type="button" onClick={() => setPaperInstructions(p.text)}
                          className="text-xs px-2.5 py-1 rounded-full border border-black/15 hover:border-[#FC8019] hover:text-[#FC8019] transition-all font-medium">
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea rows={5} value={paperInstructions} onChange={e => setPaperInstructions(e.target.value)}
                    placeholder="General instructions printed at top of paper…"
                    className={INPUT_CLS} />
                </div>

                {/* Toggles */}
                <div className="space-y-3">
                  {[
                    { label: "Include Answer Key", checked: includeAnswerKey, set: setIncludeAnswerKey },
                    { label: "Include Marking Scheme", checked: includeMarkingScheme, set: setIncludeMarkingScheme },
                  ].map(({ label, checked, set }) => (
                    <label key={label} className="flex items-center justify-between cursor-pointer">
                      <span className="text-sm font-medium text-[#1E1E1E]">{label}</span>
                      <div onClick={() => set(!checked)}
                        className={`relative w-11 h-6 rounded-full transition-all cursor-pointer ${checked ? "bg-[#FC8019]" : "bg-[#D1D5DB]"}`}>
                        <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-6" : "translate-x-1"}`} />
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Right — summary + generate */}
              <div className="space-y-4">
                <div className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm">
                  <h3 className="font-bold text-[#1E1E1E] mb-4">Paper Summary</h3>
                  <dl className="space-y-2 text-sm">
                    {[
                      ["Board", board],
                      ["Class", classLevel],
                      ["Subject", subject],
                      ["Chapters", `${(availableChapters.length > 0 ? chapters : customChapters.split("\n").filter(Boolean)).length} selected`],
                      ["Total Marks", `${computedTotal} computed / ${totalMarks} target`],
                      ["Duration", `${duration} min`],
                      ["Sets", `${variants} set${variants > 1 ? "s (shuffled)" : ""}`],
                    ].map(([k, v]) => (
                      <div key={String(k)} className="flex justify-between">
                        <dt className="text-[#4B5563]">{k}</dt>
                        <dd className="font-semibold text-[#1E1E1E]">{v}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="mt-4 rounded-xl bg-[#F3F4F6] px-3 py-2 space-y-1">
                    <p className="text-xs text-[#4B5563]">
                      📊 Est. tokens: ~{estimatedTokens.toLocaleString()}
                    </p>
                    <p className="text-xs text-[#4B5563]">
                      ⏱ Est. time: ~{estimatedSec}–{estimatedSec + 30}s
                    </p>
                    <p className="text-xs text-[#4B5563]">
                      🤖 Model: auto-selected per section difficulty
                    </p>
                  </div>
                </div>

                <button onClick={handleGenerate} disabled={submitting}
                  className="w-full flex items-center justify-center gap-2 bg-[#FC8019] text-white rounded-full font-bold py-4 hover:bg-[#E67315] hover:-translate-y-0.5 transition-all shadow-[0_8px_32px_rgba(252,128,25,0.15)] disabled:opacity-60 disabled:cursor-not-allowed">
                  {submitting
                    ? <span className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    : <Zap className="w-5 h-5" />}
                  {submitting ? "Submitting…" : "⚡ Generate Paper Now"}
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      {step < 4 && (
        <div className="flex items-center justify-between pt-2">
          <button type="button" onClick={back} disabled={step === 1}
            className="flex items-center gap-2 border-2 border-[#1E1E1E] rounded-full px-6 py-3 font-bold text-sm hover:bg-[#1E1E1E] hover:text-white transition-all disabled:opacity-40">
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
          <button type="button" onClick={next}
            className="flex items-center gap-2 bg-[#FC8019] text-white rounded-full px-6 py-3 font-bold text-sm hover:bg-[#E67315] hover:-translate-y-0.5 transition-all">
            Next: {STEPS[step]} <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
