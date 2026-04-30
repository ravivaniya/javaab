export type QuestionType =
  | 'mcq'
  | 'short'
  | 'long'
  | 'very_long'
  | 'fill_blank'
  | 'true_false'
  | 'assertion_reason';

export interface DifficultyMix {
  easy: number;
  medium: number;
  hard: number;
}

export interface SectionConfig {
  section_label: string;
  question_type: QuestionType;
  num_questions: number;
  marks_per_question: number;
  instructions?: string;
}

export interface PaperConfig {
  board: string;
  class_level: number;
  subject: string;
  chapters: string[];
  difficulty_mix: DifficultyMix;
  sections: SectionConfig[];
  total_marks: number;
  duration_minutes: number;
  num_variants: number;
  include_answer_key: boolean;
  include_marking_scheme: boolean;
  language: string;
  institute_name?: string;
  institute_logo_url?: string;
  exam_title: string;
  paper_instructions?: string;
}

export interface GeneratedQuestion {
  question_id: string;
  question_text: string;
  question_type: QuestionType;
  marks: number;
  difficulty: string;
  chapter: string;
  topic: string;
  options: string[];
  correct_answer: string;
  marking_scheme: string;
  bloom_level: string;
}

export interface PaperVariant {
  variant_label: string;
  sections: Record<string, GeneratedQuestion[]>;
  paper_html: string;
  answer_key_html: string;
  marking_scheme_html: string;
}

export interface GenerationStats {
  time_seconds: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  models_used: string[];
}

export interface GeneratedPaper {
  id: string;
  teacher_id: string;
  config: PaperConfig;
  variants: PaperVariant[];
  created_at: string;
  status: 'generating' | 'ready' | 'failed';
  exam_title: string;
  subject: string;
  class_level: number;
  board: string;
  total_marks: number;
  duration_minutes: number;
  num_variants: number;
  chapters_count: number;
  generation_stats?: GenerationStats;
}
