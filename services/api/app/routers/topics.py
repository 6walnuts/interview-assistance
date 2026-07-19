from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import LearningTopic, User, UserSkillProfile
from ..schemas import MasteryOut, TopicOut
from ..security import get_current_user

router = APIRouter(prefix="/api/topics", tags=["topics"])


def _mastery_map(db: Session, user_id: str) -> dict[str, UserSkillProfile]:
    skills = db.scalars(select(UserSkillProfile).where(UserSkillProfile.user_id == user_id))
    return {s.topic_id: s for s in skills}


def _to_out(topic: LearningTopic, skill: UserSkillProfile | None) -> TopicOut:
    mastery = None
    if skill is not None:
        mastery = MasteryOut(
            skill_level=skill.skill_level, mastery_score=skill.mastery_score,
            last_practiced_at=skill.last_practiced_at, review_due_at=skill.review_due_at,
        )
    return TopicOut(id=topic.id, slug=topic.slug, name=topic.name, category=topic.category,
                    description=topic.description, difficulty=topic.difficulty, mastery=mastery)


@router.get("", response_model=list[TopicOut])
def list_topics(
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopicOut]:
    query = select(LearningTopic).where(LearningTopic.status == "active")
    if category:
        query = query.where(LearningTopic.category == category)
    skills = _mastery_map(db, user.id)
    return [_to_out(t, skills.get(t.id)) for t in db.scalars(query.order_by(LearningTopic.name))]


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(
    topic_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TopicOut:
    topic = db.get(LearningTopic, topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    return _to_out(topic, _mastery_map(db, user.id).get(topic.id))
