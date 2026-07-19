"use client";

import type {
  AuthResponse,
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

  createInterview: (config: {
    interview_type: string;
    role: string;
    level: string;
    company_style: string;
    duration_minutes: number;
    difficulty: string;
    language: string;
    focus_areas: string[];
  }) =>
    request<{ session: InterviewSession; question: Question; opening_message: Message }>(
      "/api/interviews",
      { method: "POST", body: JSON.stringify(config) }
    ),
  getInterview: (id: string) => request<InterviewDetail>(`/api/interviews/${id}`),
  sendMessage: (id: string, content: string, action = "message") =>
    request<{ message: Message; current_stage: string }>(`/api/interviews/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, action }),
    }),
  runCode: (id: string, code: string, label: "run" | "submit") =>
    request<{ execution: Execution }>(`/api/interviews/${id}/run-code`, {
      method: "POST",
      body: JSON.stringify({ code, language: "python", label }),
    }),
  endInterview: (id: string) =>
    request<{ report_id: string; review_task_count: number }>(`/api/interviews/${id}/end`, {
      method: "POST",
    }),
  getReport: (id: string) => request<Report>(`/api/interviews/${id}/report`),

  progress: () => request<ProgressOverview>("/api/progress"),
  skills: () => request<Skill[]>("/api/progress/skills"),
  interviewHistory: () => request<InterviewHistoryItem[]>("/api/progress/interviews"),

  coachChat: (message: string, mode: string, topicSlug?: string) =>
    request<{ reply: string; suggested_actions: string[] }>("/api/coach/chat", {
      method: "POST",
      body: JSON.stringify({ message, mode, topic_slug: topicSlug ?? null }),
    }),
};
