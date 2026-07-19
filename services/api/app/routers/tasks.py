from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import LearningTask, LearningTopic, User, UserSkillProfile
from ..schemas import TaskOut
from ..security import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _to_out(task: LearningTask) -> TaskOut:
    return TaskOut(
        id=task.id, title=task.title, description=task.description, task_type=task.task_type,
        topic_slug=task.topic_slug, source=task.source, source_session_id=task.source_session_id,
        status=task.status, due_at=task.due_at, payload=task.payload, created_at=task.created_at,
    )


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    query = select(LearningTask).where(LearningTask.user_id == user.id)
    if status_filter:
        query = query.where(LearningTask.status == status_filter)
    tasks = db.scalars(query.order_by(LearningTask.created_at.desc()))
    return [_to_out(t) for t in tasks]


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TaskOut:
    task = db.get(LearningTask, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your task")
    if task.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Task already completed")

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)

    # Completing a task nudges mastery for its topic.
    if task.topic_slug:
        topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == task.topic_slug)).first()
        if topic:
            skill = db.scalars(select(UserSkillProfile).where(
                UserSkillProfile.user_id == user.id, UserSkillProfile.topic_id == topic.id,
            )).first()
            if skill is None:
                skill = UserSkillProfile(user_id=user.id, topic_id=topic.id)
                db.add(skill)
            skill.mastery_score = min(100, skill.mastery_score + 10)
            skill.skill_level = min(5, skill.mastery_score // 20)
            skill.last_practiced_at = datetime.now(timezone.utc)
    db.commit()
    return _to_out(task)
