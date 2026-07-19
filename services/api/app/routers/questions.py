"""Question-bank browser: list/filter questions, start an interview from one."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Question, User
from ..schemas import QuestionSummary
from ..security import get_current_user

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionSummary])
def list_questions(
    interview_type: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionSummary]:
    stmt = select(Question).where(Question.status == "active")
    if interview_type:
        stmt = stmt.where(Question.interview_type == interview_type)
    if category:
        stmt = stmt.where(Question.category == category)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    questions = db.scalars(stmt.order_by(Question.category, Question.difficulty, Question.title))
    return [
        QuestionSummary(
            id=q.id, title=q.title, interview_type=q.interview_type,
            category=q.category, difficulty=q.difficulty,
            prompt_preview=q.prompt[:220] + ("…" if len(q.prompt) > 220 else ""),
        )
        for q in questions
    ]
