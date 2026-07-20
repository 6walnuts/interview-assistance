// Mirrors services/api/app/schemas.py

export type InterviewType = "coding" | "system_design";
export type Level = "junior" | "mid" | "senior" | "staff";
export type Difficulty = "easy" | "medium" | "hard";

export interface UserOut {
  id: string;
  email: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface Profile {
  target_role: string;
  current_level: Level;
  target_level: Level;
  target_companies: string[];
  interview_date: string | null;
  weekly_hours: number;
  preferred_language: string;
  locale: string;
  strengths: string[];
  weaknesses: string[];
  onboarding_completed: boolean;
  resume_text: string;
  target_jd: string;
}

export interface QuestionSummary {
  id: string;
  title: string;
  interview_type: string;
  category: string;
  difficulty: string;
  prompt_preview: string;
  custom: boolean;
}

export interface Topic {
  id: string;
  slug: string;
  name: string;
  category: string;
  description: string;
  difficulty: number;
  mastery: {
    skill_level: number;
    mastery_score: number;
    last_practiced_at: string | null;
    review_due_at: string | null;
  } | null;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  task_type: string;
  topic_slug: string | null;
  source: string;
  source_session_id: string | null;
  status: string;
  due_at: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface InterviewSession {
  id: string;
  interview_type: InterviewType;
  role: string;
  level: Level;
  company_style: string;
  duration_minutes: number;
  difficulty: Difficulty;
  language: string;
  current_stage: string;
  status: string;
  started_at: string;
  ended_at: string | null;
}

export interface Question {
  id: string;
  title: string;
  prompt: string;
  examples: unknown[];
  constraints: unknown[];
  difficulty: string;
}

export interface Message {
  id: string;
  role: "interviewer" | "candidate" | "system";
  content: string;
  stage: string;
  created_at: string;
}

export interface InterviewDetail {
  session: InterviewSession;
  question: Question | null;
  messages: Message[];
}

export interface TestResult {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Execution {
  stdout: string;
  stderr: string;
  exit_code: number;
  timed_out: boolean;
  duration_ms: number;
  test_results: TestResult[];
}

export interface Report {
  session_id: string;
  interview_summary: string;
  overall_score: number;
  hire_signal: string;
  level_assessment: string;
  scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  key_mistakes: string[];
  missed_opportunities: string[];
  hints_used: string[];
  evidence: string[];
  ideal_answer_outline: string[];
  recommended_practice: string[];
  next_interview_focus: string[];
}

export interface ProgressOverview {
  streak_days: number;
  tasks_completed: number;
  tasks_pending: number;
  interviews_completed: number;
  avg_recent_score: number | null;
  weak_topics: string[];
}

export interface Skill {
  topic_slug: string;
  name: string;
  category: string;
  skill_level: number;
  mastery_score: number;
  last_practiced_at: string | null;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  difficulty: number;
}

export interface Quiz {
  topic_id: string;
  topic_slug: string;
  topic_name: string;
  questions: QuizQuestion[];
}

export interface QuizResultItem {
  question_id: string;
  question: string;
  options: string[];
  selected_index: number;
  correct_index: number;
  is_correct: boolean;
  explanation: string;
}

export interface QuizResult {
  correct: number;
  total: number;
  mastery_score: number;
  skill_level: number;
  completed_task_ids: string[];
  results: QuizResultItem[];
}

export interface PlanTask {
  id: string;
  week: number;
  title: string;
  description: string;
  task_type: string;
  topic_slug: string | null;
  status: string;
  due_at: string | null;
}

export interface StudyPlan {
  summary: string;
  weeks: number;
  task_count: number;
  tasks: PlanTask[];
}

export interface InterviewHistoryItem {
  session_id: string;
  interview_type: string;
  role: string;
  level: string;
  overall_score: number | null;
  hire_signal: string | null;
  ended_at: string | null;
}
