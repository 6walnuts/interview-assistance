from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import learning_planner
from ..db import get_db
from ..models import LearningTask, LearningTopic, User, UserProfile
from ..schemas import PlanTaskOut, StudyPlanResponse
from ..security import get_current_user

router = APIRouter(prefix="/api/plan", tags=["plan"])

PLAN_SOURCE = "study_plan"


def _week_of(task: LearningTask, start: datetime) -> int:
    if task.due_at is None:
        return 1
    due = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
    return max(1, (due - start).days // 7 + 1)


@router.post("/generate", response_model=StudyPlanResponse)
def generate_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StudyPlanResponse:
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if profile is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Complete onboarding before generating a study plan")
    topics = list(db.scalars(select(LearningTopic).where(LearningTopic.status == "active")))
    plan = learning_planner.generate_study_plan(profile, topics)

    # Regenerating replaces the previous plan's still-pending tasks; completed
    # tasks are kept as history.
    stale = db.scalars(select(LearningTask).where(
        LearningTask.user_id == user.id, LearningTask.source == PLAN_SOURCE,
        LearningTask.status == "pending"))
    for task in stale:
        db.delete(task)

    start = datetime.now(timezone.utc)
    created: list[LearningTask] = []
    for item in plan.tasks:
        task = LearningTask(
            user_id=user.id, topic_slug=item.topic_slug, task_type=item.task_type,
            title=item.title, description=item.description,
            payload={"week": item.week}, source=PLAN_SOURCE,
            due_at=start + timedelta(days=7 * item.week - 1),
        )
        db.add(task)
        created.append(task)
    db.commit()

    return StudyPlanResponse(
        summary=plan.summary, weeks=plan.weeks, task_count=len(created),
        tasks=[PlanTaskOut(id=t.id, week=int(t.payload.get("week", 1)), title=t.title,
                           description=t.description, task_type=t.task_type,
                           topic_slug=t.topic_slug, status=t.status, due_at=t.due_at)
               for t in created],
    )


@router.get("", response_model=StudyPlanResponse)
def get_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StudyPlanResponse:
    tasks = list(db.scalars(select(LearningTask).where(
        LearningTask.user_id == user.id, LearningTask.source == PLAN_SOURCE,
    ).order_by(LearningTask.due_at)))
    if not tasks:
        return StudyPlanResponse(summary="", weeks=0, task_count=0, tasks=[])
    weeks = max(int(t.payload.get("week", 1)) for t in tasks)
    return StudyPlanResponse(
        summary="", weeks=weeks, task_count=len(tasks),
        tasks=[PlanTaskOut(id=t.id, week=int(t.payload.get("week", 1)), title=t.title,
                           description=t.description, task_type=t.task_type,
                           topic_slug=t.topic_slug, status=t.status, due_at=t.due_at)
               for t in tasks],
    )
