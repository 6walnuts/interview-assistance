"""Review Task Generator Agent: interview report -> personalized learning plan.

This is the platform's core loop closure.
"""
import json

from ..models import InterviewSession, UserProfile
from .agent_schemas import GeneratedTask, NextMockInterview, ReviewPlan, ScoringReport
from .llm import complete_json
from .prompts import REVIEW_TASKS_SYSTEM, language_instruction


def _mock_plan(session: InterviewSession, report: ScoringReport) -> ReviewPlan:
    weaknesses = report.weaknesses or ["insufficient edge-case testing"]
    primary = weaknesses[0]
    topic = "idempotency" if session.interview_type == "system_design" else "arrays"
    return ReviewPlan(
        diagnosed_weaknesses=weaknesses[:3],
        recommended_topics=[topic, "testing"],
        review_tasks=[GeneratedTask(
            diagnosed_weakness=primary, topic_slug=topic, task_type="learn",
            title=f"Study the core concepts behind: {primary}",
            description="Read the concept card, then explain it back in your own words.",
            payload={"mode": "explain"})],
        practice_tasks=[GeneratedTask(
            diagnosed_weakness=primary, topic_slug=topic, task_type="practice",
            title="Complete 5 edge-case testing drills",
            description="For each problem, enumerate boundary conditions before coding.",
            payload={"count": 5, "difficulty": session.difficulty})],
        quiz_tasks=[GeneratedTask(
            diagnosed_weakness=primary, topic_slug=topic, task_type="quiz",
            title=f"Pass the {topic} quiz",
            description="Score at least 4/5 on the topic quiz.",
            payload={"num_questions": 5})],
        next_mock_interview=NextMockInterview(
            interview_type=session.interview_type, difficulty=session.difficulty,
            focus_areas=report.next_interview_focus[:3], recommended_in_days=3),
    )


def generate_review_plan(
    session: InterviewSession,
    profile: UserProfile | None,
    report: ScoringReport,
    topic_slugs: list[str],
    locale: str = "en",
) -> ReviewPlan:
    system = language_instruction(locale) + REVIEW_TASKS_SYSTEM.format(
        level=session.level, role=session.role,
        weekly_hours=profile.weekly_hours if profile else 5,
        topic_slugs=", ".join(topic_slugs) or "(none)",
    )
    messages = [{"role": "user", "content": json.dumps(report.model_dump(), default=str)}]
    return complete_json(system, messages, ReviewPlan, lambda: _mock_plan(session, report))
