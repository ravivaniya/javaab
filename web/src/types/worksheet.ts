export type WorksheetType = 'dpp' | 'worksheet' | 'revision' | 'homework' | 'mcq_drill';

export interface WorksheetConfig {
  board: string;
  class_level: number;
  subject: string;
  topic: string;
  chapter: string;
  worksheet_type: WorksheetType;
  num_questions: number;
  difficulty: string;
  include_theory_summary: boolean;
  include_hints: boolean;
  include_answer_key: boolean;
  language: string;
  institute_name?: string;
  date_field: boolean;
  student_name_field: boolean;
}

export interface WorksheetQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  marks: number;
  hint: string;
  correct_answer: string;
  solution_steps: string;
}

export interface GeneratedWorksheet {
  id: string;
  teacher_id: string;
  config: WorksheetConfig;
  theory_summary: string;
  questions: WorksheetQuestion[];
  worksheet_html: string;
  answer_key_html: string;
  created_at: string;
  status: 'generating' | 'ready' | 'failed';
  topic: string;
  subject: string;
  class_level: number;
  board: string;
  worksheet_type: WorksheetType;
  num_questions: number;
  chapter: string;
}
