from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import coach as coach_agent
from ..db import get_db
from ..models import LearningTopic, User, UserProfile, UserSkillProfile
from ..schemas import CoachChatRequest, CoachChatResponse
from ..security import get_current_user

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/chat", response_model=CoachChatResponse)
def chat(
    body: CoachChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CoachChatResponse:
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    skill = None
    if body.topic_slug:
        topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == body.topic_slug)).first()
        if topic:
            skill = db.scalars(select(UserSkillProfile).where(
                UserSkillProfile.user_id == user.id, UserSkillProfile.topic_id == topic.id,
            )).first()
    history = [{"role": t.role, "content": t.content} for t in body.history]
    reply = coach_agent.chat(body.message, body.mode, body.topic_slug, profile, skill,
                             history=history)
    return CoachChatResponse(reply=reply.reply, suggested_actions=reply.suggested_actions)
