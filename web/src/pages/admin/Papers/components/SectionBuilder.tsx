import { GripVertical, Trash2, Plus } from "lucide-react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { SectionConfig, QuestionType } from "@/types/paper";

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "mcq", label: "MCQ (Multiple Choice)" },
  { value: "short", label: "Short Answer (2–3 marks)" },
  { value: "long", label: "Long Answer (5 marks)" },
  { value: "very_long", label: "Very Long (8–10 marks)" },
  { value: "fill_blank", label: "Fill in the Blank" },
  { value: "true_false", label: "True / False" },
  { value: "assertion_reason", label: "Assertion-Reason (CBSE)" },
];

interface SortableSectionProps {
  id: string;
  section: SectionConfig;
  index: number;
  onChange: (updated: SectionConfig) => void;
  onRemove: () => void;
}

function SortableSection({ id, section, index, onChange, onRemove }: SortableSectionProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  const subtotal = section.num_questions * section.marks_per_question;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-white rounded-3xl border border-black/5 p-6 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-[#4B5563] hover:text-[#1E1E1E] p-1"
          aria-label="Drag to reorder"
        >
          <GripVertical className="w-5 h-5" />
        </button>
        <span className="text-sm font-bold text-[#4B5563]">Section {index + 1}</span>
        <button
          type="button"
          onClick={onRemove}
          className="p-1 text-[#4B5563] hover:text-rose-500 transition-colors"
          aria-label="Remove section"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-semibold text-[#4B5563] mb-1 block">Section Label</label>
          <input
            type="text"
            value={section.section_label}
            onChange={e => onChange({ ...section, section_label: e.target.value })}
            placeholder="Section A"
            className="w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-[#4B5563] mb-1 block">Question Type</label>
          <select
            value={section.question_type}
            onChange={e => onChange({ ...section, question_type: e.target.value as QuestionType })}
            className="w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all text-sm"
          >
            {QUESTION_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-[#4B5563] mb-1 block">Number of Questions</label>
          <input
            type="number"
            min={1}
            max={50}
            value={section.num_questions}
            onChange={e => onChange({ ...section, num_questions: Math.max(1, Number(e.target.value)) })}
            className="w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-[#4B5563] mb-1 block">Marks per Question</label>
          <input
            type="number"
            min={1}
            max={20}
            value={section.marks_per_question}
            onChange={e => onChange({ ...section, marks_per_question: Math.max(1, Number(e.target.value)) })}
            className="w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all text-sm"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="text-xs font-semibold text-[#4B5563] mb-1 block">Instructions (optional)</label>
          <input
            type="text"
            value={section.instructions ?? ""}
            onChange={e => onChange({ ...section, instructions: e.target.value })}
            placeholder="e.g. Attempt any 5 of the following"
            className="w-full rounded-2xl border border-black/10 px-4 py-3 focus:border-primary focus:ring-2 focus:ring-primary/20 bg-white text-[#1E1E1E] font-medium outline-none transition-all text-sm"
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
          Subtotal: {subtotal} mark{subtotal !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}

interface Props {
  sections: SectionConfig[];
  onChange: (sections: SectionConfig[]) => void;
  targetMarks: number;
}

export default function SectionBuilder({ sections, onChange, targetMarks }: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  const ids = sections.map((_, i) => `section-${i}`);
  const totalComputed = sections.reduce((acc, s) => acc + s.num_questions * s.marks_per_question, 0);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = ids.indexOf(active.id as string);
    const to = ids.indexOf(over.id as string);
    onChange(arrayMove(sections, from, to));
  };

  const addSection = () => {
    const label = String.fromCharCode(65 + sections.length);
    onChange([
      ...sections,
      { section_label: `Section ${label}`, question_type: "mcq", num_questions: 10, marks_per_question: 1, instructions: "" },
    ]);
  };

  const updateSection = (idx: number, updated: SectionConfig) => {
    const next = [...sections];
    next[idx] = updated;
    onChange(next);
  };

  const removeSection = (idx: number) => {
    onChange(sections.filter((_, i) => i !== idx));
  };

  const totalColor =
    totalComputed === targetMarks ? "text-emerald-600" : totalComputed > targetMarks ? "text-amber-600" : "text-rose-600";

  return (
    <div className="space-y-4">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {sections.map((section, idx) => (
            <SortableSection
              key={`section-${idx}`}
              id={`section-${idx}`}
              section={section}
              index={idx}
              onChange={updated => updateSection(idx, updated)}
              onRemove={() => removeSection(idx)}
            />
          ))}
        </SortableContext>
      </DndContext>

      <button
        type="button"
        onClick={addSection}
        className="w-full border-2 border-dashed border-black/20 rounded-3xl py-4 text-[#4B5563] font-semibold hover:border-primary hover:text-primary transition-all flex items-center justify-center gap-2"
      >
        <Plus className="w-5 h-5" /> Add Section
      </button>

      <div className={`sticky bottom-0 bg-white/90 backdrop-blur rounded-2xl border border-black/5 px-6 py-3 flex items-center justify-between shadow-md`}>
        <span className="text-sm text-[#4B5563]">Target: <b>{targetMarks}</b> marks</span>
        <span className={`text-sm font-bold ${totalColor}`} data-testid="total-marks-display">
          Total: {totalComputed} / {targetMarks} marks
        </span>
      </div>
    </div>
  );
}
