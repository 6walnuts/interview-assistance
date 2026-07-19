import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import coach as coach_agent
from ..agents.llm import AgentError
from ..db import get_db
from ..models import LearningTopic, Question, User, UserProfile, UserSkillProfile
from ..schemas import CoachChatRequest, CoachChatResponse
from ..security import get_current_user

router = APIRouter(prefix="/api/coach", tags=["coach"])


def _chat_context(body: CoachChatRequest, user: User, db: Session):
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    skill = None
    if body.topic_slug:
        topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == body.topic_slug)).first()
        if topic:
            skill = db.scalars(select(UserSkillProfile).where(
                UserSkillProfile.user_id == user.id, UserSkillProfile.topic_id == topic.id,
            )).first()
    history = [{"role": t.role, "content": t.content} for t in body.history]
    question = db.get(Question, body.question_id) if body.question_id else None
    return profile, skill, history, question


@router.post("/chat", response_model=CoachChatResponse)
def chat(
    body: CoachChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CoachChatResponse:
    profile, skill, history, question = _chat_context(body, user, db)
    reply = coach_agent.chat(body.message, body.mode, body.topic_slug, profile, skill,
                             history=history, question=question)
    return CoachChatResponse(reply=reply.reply, suggested_actions=reply.suggested_actions,
                             code_snippet=reply.code_snippet)


@router.post("/chat/stream")
def chat_stream(
    body: CoachChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StreamingResponse:
    """SSE variant: `data: {"delta": ...}` chunks of the reply as it streams,
    then a final `data: {"done": true, ...}` event with the full payload."""
    profile, skill, history, question = _chat_context(body, user, db)

    def events():
        try:
            for kind, payload in coach_agent.chat_stream(
                body.message, body.mode, body.topic_slug, profile, skill, history=history,
                question=question,
            ):
                if kind == "delta":
                    yield f"data: {json.dumps({'delta': payload})}\n\n"
                else:
                    yield "data: " + json.dumps({
                        "done": True,
                        "reply": payload.reply,
                        "suggested_actions": payload.suggested_actions,
                        "code_snippet": payload.code_snippet,
                    }) + "\n\n"
        except AgentError as exc:
            # Streaming already returned 200; deliver the error in-band.
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
