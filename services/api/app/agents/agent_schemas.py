"""Structured output schemas for every agent (validated on each call)."""
from typing import Literal

from pydantic import BaseModel, Field

Stage = Literal[
    "introduction", "question_presentation", "clarification", "approach",
    "deep_dive", "coding", "testing", "complexity", "optimization",
    "follow_up", "candidate_questions", "finish",
]

HireSignal = Literal[
    "strong_no_hire", "no_hire", "lean_no_hire", "mixed",
    "lean_hire", "hire", "strong_hire",
]


class InternalObservation(BaseModel):
    candidate_signal: str = ""
    strength_detected: str | None = None
    weakness_detected: str | None = None
    mistake_detected: str | None = None
    recommended_follow_up: str = ""
    hint_level: int = Field(default=0, ge=0, le=3)


class InterviewerTurn(BaseModel):
    message: str
    stage: Stage
    action: Literal["wait_for_candidate", "end_interview"] = "wait_for_candidate"
    internal_observation: InternalObservation = InternalObservation()


class ScoringReport(BaseModel):
    interview_summary: str
    overall_score: float = Field(ge=1, le=5)
    hire_signal: HireSignal
    level_assessment: str = ""
    scores: dict[str, int] = {}
    strengths: list[str] = []
    weaknesses: list[str] = []
    key_mistakes: list[str] = []
    missed_opportunities: list[str] = []
    hints_used: list[str] = []
    evidence: list[str] = []
    ideal_answer_outline: list[str] = []
    recommended_practice: list[str] = []
    next_interview_focus: list[str] = []


class GeneratedTask(BaseModel):
    diagnosed_weakness: str = ""
    topic_slug: str | None = None
    task_type: Literal["learn", "practice", "quiz", "design_drill", "mock_interview"] = "learn"
    title: str
    description: str = ""
    payload: dict = {}


class NextMockInterview(BaseModel):
    interview_type: Literal["coding", "system_design"] = "coding"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    focus_areas: list[str] = []
    recommended_in_days: int = 3


class ReviewPlan(BaseModel):
    diagnosed_weaknesses: list[str] = []
    recommended_topics: list[str] = []
    review_tasks: list[GeneratedTask] = []
    practice_tasks: list[GeneratedTask] = []
    quiz_tasks: list[GeneratedTask] = []
    next_mock_interview: NextMockInterview = NextMockInterview()


class CoachReply(BaseModel):
    reply: str
    suggested_actions: list[str] = []


class GeneratedQuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2, max_length=6)
    answer_index: int = Field(ge=0)
    explanation: str = ""
    difficulty: int = Field(default=2, ge=1, le=5)


class GeneratedQuiz(BaseModel):
    questions: list[GeneratedQuizQuestion]


class PlanTask(BaseModel):
    week: int = Field(ge=1, le=16)
    topic_slug: str | None = None
    task_type: Literal["learn", "practice", "quiz", "design_drill", "mock_interview"] = "learn"
    title: str
    description: str = ""


class StudyPlan(BaseModel):
    summary: str
    weeks: int = Field(ge=1, le=16)
    tasks: list[PlanTask]
