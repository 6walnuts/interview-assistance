"""Learning Planner Agent: profile + timeline -> week-by-week study plan."""
from datetime import date

from ..models import LearningTopic, UserProfile
from .agent_schemas import PlanTask, StudyPlan
from .llm import complete_json
from .prompts import STUDY_PLAN_SYSTEM, language_instruction

DEFAULT_WEEKS = 4
MAX_WEEKS = 12


def plan_weeks(profile: UserProfile) -> int:
    if profile.interview_date:
        days = (profile.interview_date - date.today()).days
        return max(1, min(MAX_WEEKS, days // 7))
    return DEFAULT_WEEKS


def _mock_plan(profile: UserProfile, weeks: int, topic_slugs: list[str]) -> StudyPlan:
    focus = [w for w in (profile.weaknesses or []) if w in topic_slugs]
    fillers = [s for s in ("arrays", "hash-map", "binary-search", "caching",
                           "api-design", "sharding", "fault-tolerance") if s in topic_slugs]
    queue = focus + [s for s in fillers if s not in focus]
    tasks: list[PlanTask] = []
    for week in range(1, weeks + 1):
        slug_a = queue[(week * 2 - 2) % len(queue)] if queue else None
        slug_b = queue[(week * 2 - 1) % len(queue)] if queue else None
        if week == weeks:
            tasks += [
                PlanTask(week=week, topic_slug=slug_a, task_type="practice",
                         title="Review your mistake list",
                         description="Re-test every item recorded in common mistakes this cycle."),
                PlanTask(week=week, task_type="mock_interview",
                         title="Take a full mock interview",
                         description="Final rehearsal at target difficulty across your weak areas."),
            ]
            continue
        tasks += [
            PlanTask(week=week, topic_slug=slug_a, task_type="learn",
                     title=f"Study {slug_a or 'a core topic'}",
                     description="Read the concept card and note the interview-relevant tradeoffs."),
            PlanTask(week=week, topic_slug=slug_a, task_type="quiz",
                     title=f"Pass the {slug_a or 'topic'} quiz",
                     description="Score at least 4/5 on the chapter quiz."),
            PlanTask(week=week, topic_slug=slug_b, task_type="practice",
                     title=f"Drill {slug_b or 'a second topic'}",
                     description="Complete focused practice problems on this topic."),
        ]
        if week >= 2:
            tasks.append(PlanTask(
                week=week, task_type="mock_interview",
                title="Take a checkpoint mock interview",
                description="Measure progress; the report will adjust your remaining plan."))
    return StudyPlan(
        summary=f"A {weeks}-week plan for a {profile.target_level} {profile.target_role}: "
                "weak areas first, weekly quiz checkpoints, and a mock interview from week 2 "
                "onward to keep the feedback loop running.",
        weeks=weeks, tasks=tasks,
    )


def generate_study_plan(profile: UserProfile, topics: list[LearningTopic]) -> StudyPlan:
    weeks = plan_weeks(profile)
    topic_slugs = [t.slug for t in topics]
    system = language_instruction(profile.locale) + STUDY_PLAN_SYSTEM.format(
        level=profile.current_level, role=profile.target_role,
        target_level=profile.target_level, weeks=weeks,
        weekly_hours=profile.weekly_hours,
        strengths=", ".join(profile.strengths or []) or "(none given)",
        weaknesses=", ".join(profile.weaknesses or []) or "(none given)",
        resume=(profile.resume_text or "").strip()[:2000] or "(none provided)",
        topic_slugs=", ".join(topic_slugs),
    )
    messages = [{"role": "user", "content": "Generate the study plan now."}]
    plan = complete_json(system, messages, StudyPlan,
                         lambda: _mock_plan(profile, weeks, topic_slugs))
    # Clamp weeks and drop tasks referencing unknown topics.
    known = set(topic_slugs)
    for task in plan.tasks:
        if task.topic_slug and task.topic_slug not in known:
            task.topic_slug = None
    plan.weeks = max(1, min(plan.weeks, MAX_WEEKS))
    return plan
