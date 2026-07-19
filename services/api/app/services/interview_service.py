"""Interview orchestration: planner -> interviewer -> sandbox -> scorer -> review tasks."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import interviewer, planner, review_tasks, scorer
from ..agents.agent_schemas import ReviewPlan, ScoringReport
from ..models import (
    CandidateCodeVersion,
    CodeExecutionResult,
    InterviewMessage,
    InterviewReport,
    InterviewScore,
    InterviewSession,
    LearningTask,
    LearningTopic,
    Question,
    ReviewTask,
    User,
    UserProfile,
    UserSkillProfile,
)
from .sandbox import ExecutionResult, run_code as sandbox_run_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _locale(db: Session, user_id: str) -> str:
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    return profile.locale if profile else "en"


RESUME_EXCERPT_CHARS = 2000


def _resume(db: Session, user_id: str) -> str:
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    text = (profile.resume_text or "").strip() if profile else ""
    return text[:RESUME_EXCERPT_CHARS]


def create_session(db: Session, user: User, config: dict) -> tuple[InterviewSession, Question, InterviewMessage]:
    question_id = config.pop("question_id", None)
    if question_id:
        # Explicit pick from the question-bank browser.
        question = db.get(Question, question_id)
        if question is None or question.interview_type != config["interview_type"]:
            raise ValueError("Selected question not found for this interview type.")
    else:
        question = planner.pick_question(
            db,
            interview_type=config["interview_type"],
            difficulty=config["difficulty"],
            focus_areas=config.get("focus_areas", []),
            user_id=user.id,
        )
    if question is None:
        raise ValueError("No question available for this interview type. Run the seed script.")

    session = InterviewSession(user_id=user.id, question_id=question.id, **config)
    db.add(session)
    db.flush()

    turn = interviewer.next_turn(session, question, transcript=[], action="message",
                                 locale=_locale(db, user.id), resume=_resume(db, user.id))
    session.current_stage = turn.stage
    opening = InterviewMessage(
        session_id=session.id, role="interviewer", content=turn.message,
        stage=turn.stage, internal_observation=turn.internal_observation.model_dump(),
    )
    db.add(opening)
    db.commit()
    return session, question, opening


def _transcript(db: Session, session_id: str) -> list[dict[str, str]]:
    messages = db.scalars(
        select(InterviewMessage)
        .where(InterviewMessage.session_id == session_id)
        .order_by(InterviewMessage.created_at, InterviewMessage.id)
    )
    return [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]


def _latest_execution_summary(db: Session, session_id: str) -> str:
    result = db.scalars(
        select(CodeExecutionResult)
        .where(CodeExecutionResult.session_id == session_id)
        .order_by(CodeExecutionResult.created_at.desc())
    ).first()
    if result is None:
        return ""
    passed = sum(1 for t in result.test_results if t.get("passed"))
    return (f"exit_code={result.exit_code}, timed_out={result.timed_out}, "
            f"tests passed {passed}/{len(result.test_results)}, stderr={result.stderr[:200]}")


def handle_candidate_message(
    db: Session, session: InterviewSession, content: str, action: str
) -> tuple[InterviewMessage, str]:
    """Returns the interviewer's reply and the hint_content for this turn
    (empty unless the candidate explicitly requested a hint)."""
    db.add(InterviewMessage(
        session_id=session.id, role="candidate", content=content, stage=session.current_stage,
    ))
    db.flush()

    if action == "request_hint":
        session.hint_count += 1

    turn = interviewer.next_turn(
        session, session.question, _transcript(db, session.id),
        action=action, execution_summary=_latest_execution_summary(db, session.id),
        locale=_locale(db, session.user_id), resume=_resume(db, session.user_id),
    )
    session.current_stage = turn.stage
    reply = InterviewMessage(
        session_id=session.id, role="interviewer", content=turn.message,
        stage=turn.stage, internal_observation=turn.internal_observation.model_dump(),
    )
    db.add(reply)
    db.commit()
    return reply, turn.hint_content


def run_code(
    db: Session, session: InterviewSession, code: str, language: str, label: str
) -> ExecutionResult:
    version = CandidateCodeVersion(session_id=session.id, language=language, code=code, label=label)
    db.add(version)
    db.flush()

    test_cases = session.question.test_cases if session.question else []
    result = sandbox_run_code(code, language, test_cases)

    db.add(CodeExecutionResult(
        session_id=session.id, code_version_id=version.id,
        stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code,
        timed_out=result.timed_out, duration_ms=result.duration_ms,
        test_results=result.test_results,
    ))
    db.commit()
    return result


def end_interview(
    db: Session, session: InterviewSession, generate_report: bool = True
) -> tuple[InterviewReport | None, int]:
    """Score the interview, persist the report, and close the learning loop.

    With generate_report=False the session just ends (status/ended_at); calling
    again later with generate_report=True scores it then — the report page
    offers exactly that."""
    existing = db.scalars(
        select(InterviewReport).where(InterviewReport.session_id == session.id)
    ).first()
    if existing is not None:  # idempotent
        count = len(list(db.scalars(select(ReviewTask).where(ReviewTask.session_id == session.id))))
        return existing, count

    if not generate_report:
        if session.status != "completed":
            session.status = "completed"
            session.ended_at = _now()
            db.commit()
        return None, 0

    code_versions = [
        {"label": v.label, "language": v.language, "code": v.code, "created_at": v.created_at}
        for v in db.scalars(select(CandidateCodeVersion).where(
            CandidateCodeVersion.session_id == session.id).order_by(CandidateCodeVersion.created_at))
    ]
    executions = [
        {"exit_code": r.exit_code, "timed_out": r.timed_out, "stderr": r.stderr,
         "test_results": r.test_results}
        for r in db.scalars(select(CodeExecutionResult).where(
            CodeExecutionResult.session_id == session.id).order_by(CodeExecutionResult.created_at))
    ]
    observations = [
        m.internal_observation for m in db.scalars(select(InterviewMessage).where(
            InterviewMessage.session_id == session.id)) if m.internal_observation
    ]

    locale = _locale(db, session.user_id)
    report_data: ScoringReport = scorer.score_interview(
        session, session.question, _transcript(db, session.id),
        code_versions, executions, observations, locale=locale,
    )

    report = InterviewReport(session_id=session.id, **report_data.model_dump())
    db.add(report)
    for dimension, score in report_data.scores.items():
        db.add(InterviewScore(session_id=session.id, dimension=dimension, score=score))

    session.status = "completed"
    session.ended_at = _now()

    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == session.user_id)).first()
    topic_slugs = list(db.scalars(select(LearningTopic.slug).where(LearningTopic.status == "active")))
    plan: ReviewPlan = review_tasks.generate_review_plan(session, profile, report_data,
                                                         topic_slugs, locale=locale)

    task_count = _persist_review_plan(db, session, plan)
    _update_skill_profiles(db, session, report_data, plan)
    db.commit()
    return report, task_count


def _persist_review_plan(db: Session, session: InterviewSession, plan: ReviewPlan) -> int:
    count = 0
    for task in [*plan.review_tasks, *plan.practice_tasks, *plan.quiz_tasks]:
        db.add(ReviewTask(
            session_id=session.id, user_id=session.user_id,
            diagnosed_weakness=task.diagnosed_weakness, topic_slug=task.topic_slug,
            task_type=task.task_type, title=task.title, description=task.description,
        ))
        db.add(LearningTask(
            user_id=session.user_id, topic_slug=task.topic_slug, task_type=task.task_type,
            title=task.title, description=task.description, payload=task.payload,
            source="interview_report", source_session_id=session.id,
        ))
        count += 1

    nxt = plan.next_mock_interview
    db.add(LearningTask(
        user_id=session.user_id, task_type="mock_interview",
        title=f"Take a {nxt.difficulty} {nxt.interview_type.replace('_', ' ')} mock interview",
        description="Focus areas: " + (", ".join(nxt.focus_areas) or "same as last time"),
        payload=nxt.model_dump(), source="interview_report", source_session_id=session.id,
        due_at=_now() + timedelta(days=nxt.recommended_in_days),
    ))
    return count + 1


def _update_skill_profiles(
    db: Session, session: InterviewSession, report: ScoringReport, plan: ReviewPlan
) -> None:
    for slug in plan.recommended_topics:
        topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == slug)).first()
        if topic is None:
            continue
        skill = db.scalars(select(UserSkillProfile).where(
            UserSkillProfile.user_id == session.user_id,
            UserSkillProfile.topic_id == topic.id,
        )).first()
        if skill is None:
            skill = UserSkillProfile(user_id=session.user_id, topic_id=topic.id)
            db.add(skill)
        skill.common_mistakes = list({*(skill.common_mistakes or []), *report.key_mistakes})[:10]
        skill.recommended_next_steps = report.recommended_practice[:5]
        skill.last_practiced_at = _now()
        skill.review_due_at = _now() + timedelta(days=2)
