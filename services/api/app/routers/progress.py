from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import InterviewReport, InterviewSession, LearningTask, User, UserSkillProfile
from ..schemas import InterviewHistoryItem, ProgressOverview, SkillOut
from ..security import get_current_user

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _streak_days(completed_dates: list[datetime]) -> int:
    days = {d.date() for d in completed_dates}
    streak, cursor = 0, datetime.now(timezone.utc).date()
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("", response_model=ProgressOverview)
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressOverview:
    tasks = list(db.scalars(select(LearningTask).where(LearningTask.user_id == user.id)))
    completed = [t for t in tasks if t.status == "completed"]
    sessions = list(db.scalars(select(InterviewSession).where(
        InterviewSession.user_id == user.id, InterviewSession.status == "completed")))
    reports = list(db.scalars(
        select(InterviewReport).join(InterviewSession, InterviewReport.session_id == InterviewSession.id)
        .where(InterviewSession.user_id == user.id)
        .order_by(InterviewReport.created_at.desc()).limit(5)
    ))
    skills = list(db.scalars(select(UserSkillProfile).where(UserSkillProfile.user_id == user.id)))
    weak = sorted((s for s in skills if s.mastery_score < 50), key=lambda s: s.mastery_score)
    return ProgressOverview(
        streak_days=_streak_days([t.completed_at for t in completed if t.completed_at]),
        tasks_completed=len(completed),
        tasks_pending=len([t for t in tasks if t.status == "pending"]),
        interviews_completed=len(sessions),
        avg_recent_score=round(sum(r.overall_score for r in reports) / len(reports), 2) if reports else None,
        weak_topics=[s.topic.slug for s in weak[:5]],
    )


@router.get("/skills", response_model=list[SkillOut])
def skills(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SkillOut]:
    rows = db.scalars(select(UserSkillProfile).where(UserSkillProfile.user_id == user.id))
    return [SkillOut(topic_slug=s.topic.slug, name=s.topic.name, category=s.topic.category,
                     skill_level=s.skill_level, mastery_score=s.mastery_score,
                     last_practiced_at=s.last_practiced_at) for s in rows]


@router.get("/interviews", response_model=list[InterviewHistoryItem])
def interview_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[InterviewHistoryItem]:
    sessions = db.scalars(select(InterviewSession).where(InterviewSession.user_id == user.id)
                          .order_by(InterviewSession.started_at.desc()))
    items = []
    for s in sessions:
        report = db.scalars(select(InterviewReport).where(InterviewReport.session_id == s.id)).first()
        items.append(InterviewHistoryItem(
            session_id=s.id, interview_type=s.interview_type, role=s.role, level=s.level,
            overall_score=report.overall_score if report else None,
            hire_signal=report.hire_signal if report else None, ended_at=s.ended_at,
        ))
    return items
