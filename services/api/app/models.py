"""SQLAlchemy models for all 16 tables. DDL mirror: database/init.sql."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    target_role: Mapped[str] = mapped_column(String(120), default="Software Engineer")
    current_level: Mapped[str] = mapped_column(String(40), default="mid")
    target_level: Mapped[str] = mapped_column(String(40), default="mid")
    target_companies: Mapped[list] = mapped_column(JSON, default=list)
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekly_hours: Mapped[int] = mapped_column(Integer, default=5)
    preferred_language: Mapped[str] = mapped_column(String(40), default="python")
    locale: Mapped[str] = mapped_column(String(10), default="en")  # en | zh | es
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="profile")


class LearningTopic(Base, TimestampMixin):
    __tablename__ = "learning_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    subtopics: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(20), default="active")


class UserSkillProfile(Base, TimestampMixin):
    __tablename__ = "user_skill_profiles"
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_user_topic"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_topics.id"), nullable=False)
    skill_level: Mapped[int] = mapped_column(Integer, default=0)
    mastery_score: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0)
    common_mistakes: Mapped[list] = mapped_column(JSON, default=list)
    recommended_next_steps: Mapped[list] = mapped_column(JSON, default=list)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    topic: Mapped[LearningTopic] = relationship()


class LearningTask(Base, TimestampMixin):
    __tablename__ = "learning_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    topic_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)  # learn|practice|quiz|design_drill|mock_interview
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(30), default="coach")  # interview_report|coach|onboarding
    source_session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LearningSession(Base, TimestampMixin):
    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("learning_topics.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(30), default="explain")
    summary: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    interview_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general")
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list] = mapped_column(JSON, default=list)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    test_cases: Mapped[list] = mapped_column(JSON, default=list)
    rubric: Mapped[dict] = mapped_column(JSON, default=dict)
    companies: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")


class InterviewSession(Base, TimestampMixin):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(120), default="Software Engineer")
    level: Mapped[str] = mapped_column(String(40), default="mid")
    company_style: Mapped[str] = mapped_column(String(80), default="Generic Big Tech")
    interview_type: Mapped[str] = mapped_column(String(30), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    language: Mapped[str] = mapped_column(String(40), default="python")
    focus_areas: Mapped[list] = mapped_column(JSON, default=list)
    question_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("questions.id"), nullable=True)
    current_stage: Mapped[str] = mapped_column(String(40), default="introduction")
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    question: Mapped[Question | None] = relationship()
    messages: Mapped[list["InterviewMessage"]] = relationship(
        back_populates="session", order_by="InterviewMessage.created_at"
    )


class InterviewMessage(Base, TimestampMixin):
    __tablename__ = "interview_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # interviewer|candidate|system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="introduction")
    # Interviewer-only private notes; never serialized to the frontend.
    internal_observation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped[InterviewSession] = relationship(back_populates="messages")


class CandidateCodeVersion(Base, TimestampMixin):
    __tablename__ = "candidate_code_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    language: Mapped[str] = mapped_column(String(40), default="python")
    code: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String(40), default="run")  # run|submit


class CodeExecutionResult(Base, TimestampMixin):
    __tablename__ = "code_execution_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    code_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_code_versions.id"), nullable=False
    )
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    exit_code: Mapped[int] = mapped_column(Integer, default=0)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    test_results: Mapped[list] = mapped_column(JSON, default=list)


class InterviewScore(Base, TimestampMixin):
    __tablename__ = "interview_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(60), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="")


class InterviewReport(Base, TimestampMixin):
    __tablename__ = "interview_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), unique=True, nullable=False
    )
    interview_summary: Mapped[str] = mapped_column(Text, default="")
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    hire_signal: Mapped[str] = mapped_column(String(30), default="mixed")
    level_assessment: Mapped[str] = mapped_column(String(120), default="")
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    key_mistakes: Mapped[list] = mapped_column(JSON, default=list)
    missed_opportunities: Mapped[list] = mapped_column(JSON, default=list)
    hints_used: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    ideal_answer_outline: Mapped[list] = mapped_column(JSON, default=list)
    recommended_practice: Mapped[list] = mapped_column(JSON, default=list)
    next_interview_focus: Mapped[list] = mapped_column(JSON, default=list)


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    diagnosed_weakness: Mapped[str] = mapped_column(String(255), default="")
    topic_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    task_type: Mapped[str] = mapped_column(String(30), default="learn")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")


class QuizQuestion(Base, TimestampMixin):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_topics.id"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, default=list)
    answer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(20), default="active")


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    quiz_question_id: Mapped[str] = mapped_column(String(36), ForeignKey("quiz_questions.id"), nullable=False)
    selected_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
