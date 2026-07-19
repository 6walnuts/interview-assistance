"use client";

import type {
  AuthResponse,
  QuestionSummary,
  Quiz,
  QuizResult,
  StudyPlan,
  Execution,
  InterviewDetail,
  InterviewHistoryItem,
  Message,
  Profile,
  ProgressOverview,
  Question,
  Report,
  InterviewSession,
  Skill,
  Task,
  Topic,
  UserOut,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "aic_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token === null) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, token);
}

export class ApiError extends Error {
  constructor(public status: number, detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (resp.status === 401 && typeof window !== "undefined") {
    setToken(null);
    if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
  }
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export const api = {
  health: () =>
    request<{ status: string; mock_ai: boolean; local_mode: boolean }>("/api/health"),

  register: (email: string, password: string, name: string) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getProfile: () => request<{ user: UserOut; profile: Profile }>("/api/profile"),
  updateProfile: (patch: Partial<Profile>) =>
    request<{ user: UserOut; profile: Profile }>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  listTopics: (category?: string) =>
    request<Topic[]>(`/api/topics${category ? `?category=${category}` : ""}`),

  listTasks: (status?: string) =>
    request<Task[]>(`/api/tasks${status ? `?status_filter=${status}` : ""}`),
  completeTask: (taskId: string) =>
    request<Task>(`/api/tasks/${taskId}/complete`, { method: "POST" }),

  listQuestions: (filters: { interview_type?: string; category?: string; difficulty?: string } = {}) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) if (v) params.set(k, v);
    const qs = params.toString();
    return request<QuestionSummary[]>(`/api/questions${qs ? `?${qs}` : ""}`);
  },

  createInterview: (config: {
    interview_type: string;
    role: string;
    level: string;
    company_style: string;
    duration_minutes: number;
    difficulty: string;
    language: string;
    focus_areas: string[];
    question_id?: string | null;
  }) =>
    request<{ session: InterviewSession; question: Question; opening_message: Message }>(
      "/api/interviews",
      { method: "POST", body: JSON.stringify(config) }
    ),
  getInterview: (id: string) => request<InterviewDetail>(`/api/interviews/${id}`),
  sendMessage: (id: string, content: string, action = "message", currentCode = "") =>
    request<{ message: Message; current_stage: string; hint_content: string }>(
      `/api/interviews/${id}/messages`,
      { method: "POST", body: JSON.stringify({ content, action, current_code: currentCode }) }
    ),
  runCode: (id: string, code: string, label: "run" | "submit", language = "python") =>
    request<{ execution: Execution }>(`/api/interviews/${id}/run-code`, {
      method: "POST",
      body: JSON.stringify({ code, language, label }),
    }),
  endInterview: (id: string, generateReport = true) =>
    request<{ report_id: string | null; review_task_count: number }>(`/api/interviews/${id}/end`, {
      method: "POST",
      body: JSON.stringify({ generate_report: generateReport }),
    }),
  getReport: (id: string) => request<Report>(`/api/interviews/${id}/report`),

  progress: () => request<ProgressOverview>("/api/progress"),
  skills: () => request<Skill[]>("/api/progress/skills"),
  interviewHistory: () => request<InterviewHistoryItem[]>("/api/progress/interviews"),

  getQuiz: (topicSlug: string, count = 5) =>
    request<Quiz>(`/api/quiz/${topicSlug}?count=${count}`),
  submitQuiz: (topicSlug: string, answers: { question_id: string; selected_index: number }[]) =>
    request<QuizResult>(`/api/quiz/${topicSlug}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  generatePlan: () => request<StudyPlan>("/api/plan/generate", { method: "POST" }),
  getPlan: () => request<StudyPlan>("/api/plan"),

  coachChat: (
    message: string,
    mode: string,
    topicSlug?: string,
    history: { role: "user" | "assistant"; content: string }[] = []
  ) =>
    request<{ reply: string; suggested_actions: string[]; code_snippet: string }>(
      "/api/coach/chat",
      {
        method: "POST",
        body: JSON.stringify({ message, mode, topic_slug: topicSlug ?? null, history }),
      }
    ),

  runScratch: (code: string, language = "python") =>
    request<Execution>("/api/code/run", {
      method: "POST",
      body: JSON.stringify({ code, language }),
    }),

  streamCoachChat: async (
    message: string,
    mode: string,
    topicSlug: string | undefined,
    history: { role: "user" | "assistant"; content: string }[],
    onDelta: (text: string) => void
  ): Promise<{ reply: string; suggested_actions: string[]; code_snippet: string }> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch(`${API_URL}/api/coach/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message, mode, topic_slug: topicSlug ?? null, history }),
    });
    if (!resp.ok || !resp.body) {
      let detail = resp.statusText;
      try {
        const body = await resp.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch { /* keep statusText */ }
      throw new ApiError(resp.status, detail);
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let final: { reply: string; suggested_actions: string[]; code_snippet: string } | null = null;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const raw of events) {
        const line = raw.trim();
        if (!line.startsWith("data:")) continue;
        const ev = JSON.parse(line.slice(5));
        if (ev.error) throw new ApiError(502, ev.error);
        if (ev.delta) onDelta(ev.delta as string);
        if (ev.done) final = ev;
      }
    }
    if (!final) throw new ApiError(502, "Stream ended unexpectedly");
    return final;
  },

  addVoiceTranscript: (interviewId: string, role: "candidate" | "interviewer", content: string) =>
    request<Message>("/api/voice/realtime-transcript", {
      method: "POST",
      body: JSON.stringify({ interview_id: interviewId, role, content }),
    }),
  runVoiceTool: (interviewId: string, name: string, args: Record<string, unknown>) =>
    request<{ result: Record<string, unknown>; current_stage: string }>("/api/voice/realtime-tool", {
      method: "POST",
      body: JSON.stringify({ interview_id: interviewId, name, arguments: args }),
    }),
};
