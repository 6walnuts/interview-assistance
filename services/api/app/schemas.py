"""API request/response schemas (Pydantic v2)."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

InterviewType = Literal["coding", "system_design"]
Level = Literal["junior", "mid", "senior", "staff"]
Difficulty = Literal["easy", "medium", "hard"]


# ---------- auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- profile ----------
class ProfileUpdate(BaseModel):
    target_role: str | None = None
    current_level: Level | None = None
    target_level: Level | None = None
    target_companies: list[str] | None = None
    interview_date: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=80)
    preferred_language: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    resume_text: str | None = None
    onboarding_completed: bool | None = None


class ProfileOut(BaseModel):
    target_role: str
    current_level: str
    target_level: str
    target_companies: list[str]
    interview_date: date | None
    weekly_hours: int
    preferred_language: str
    strengths: list[str]
    weaknesses: list[str]
    onboarding_completed: bool


class ProfileResponse(BaseModel):
    user: UserOut
    profile: ProfileOut


# ---------- topics ----------
class MasteryOut(BaseModel):
    skill_level: int
    mastery_score: int
    last_practiced_at: datetime | None = None
    review_due_at: datetime | None = None


class TopicOut(BaseModel):
    id: str
    slug: str
    name: str
    category: str
    description: str
    difficulty: int
    mastery: MasteryOut | None = None


# ---------- tasks ----------
class TaskOut(BaseModel):
    id: str
    title: str
    description: str
    task_type: str
    topic_slug: str | None
    source: str
    source_session_id: str | None
    status: str
    due_at: datetime | None
    payload: dict[str, Any]
    created_at: datetime


# ---------- interviews ----------
class InterviewCreate(BaseModel):
    interview_type: InterviewType
    role: str = "Software Engineer"
    level: Level = "mid"
    company_style: str = "Generic Big Tech"
    duration_minutes: int = Field(default=45, ge=15, le=90)
    difficulty: Difficulty = "medium"
    language: str = "python"
    focus_areas: list[str] = []


class QuestionOut(BaseModel):
    id: str
    title: str
    prompt: str
    examples: list[Any]
    constraints: list[Any]
    difficulty: str


class SessionOut(BaseModel):
    id: str
    interview_type: str
    role: str
    level: str
    company_style: str
    duration_minutes: int
    difficulty: str
    language: str
    current_stage: str
    status: str
    started_at: datetime
    ended_at: datetime | None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    stage: str
    created_at: datetime


class InterviewCreateResponse(BaseModel):
    session: SessionOut
    question: QuestionOut
    opening_message: MessageOut


class InterviewDetail(BaseModel):
    session: SessionOut
    question: QuestionOut | None
    messages: list[MessageOut]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    action: Literal["message", "ask_clarification", "request_hint"] = "message"


class SendMessageResponse(BaseModel):
    message: MessageOut
    current_stage: str


class RunCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50_000)
    language: Literal["python"] = "python"
    label: Literal["run", "submit"] = "run"


class TestResultOut(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class ExecutionOut(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_ms: int
    test_results: list[TestResultOut]


class RunCodeResponse(BaseModel):
    execution: ExecutionOut


class EndInterviewResponse(BaseModel):
    report_id: str
    review_task_count: int


class ReportOut(BaseModel):
    session_id: str
    interview_summary: str
    overall_score: float
    hire_signal: str
    level_assessment: str
    scores: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    key_mistakes: list[str]
    missed_opportunities: list[str]
    hints_used: list[str]
    evidence: list[str]
    ideal_answer_outline: list[str]
    recommended_practice: list[str]
    next_interview_focus: list[str]


class ReviewTaskOut(BaseModel):
    id: str
    diagnosed_weakness: str
    topic_slug: str | None
    task_type: str
    title: str
    description: str
    status: str


# ---------- progress ----------
class ProgressOverview(BaseModel):
    streak_days: int
    tasks_completed: int
    tasks_pending: int
    interviews_completed: int
    avg_recent_score: float | None
    weak_topics: list[str]


class SkillOut(BaseModel):
    topic_slug: str
    name: str
    category: str
    skill_level: int
    mastery_score: int
    last_practiced_at: datetime | None


class InterviewHistoryItem(BaseModel):
    session_id: str
    interview_type: str
    role: str
    level: str
    overall_score: float | None
    hire_signal: str | None
    ended_at: datetime | None


# ---------- coach ----------
class CoachChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    topic_slug: str | None = None
    mode: Literal[
        "explain", "summarize", "quiz", "flashcards", "guided_practice",
        "coding_drill", "system_design_drill", "review_mistakes", "daily_plan", "weekly_plan",
    ] = "explain"


class CoachChatResponse(BaseModel):
    reply: str
    suggested_actions: list[str]
