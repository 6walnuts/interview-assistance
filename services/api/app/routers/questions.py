"""Question-bank browser: list/filter, custom questions, start sessions from one."""
from fastapi import APIRouter, Depends, status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Question, User
from ..schemas import CustomQuestionCreate, QuestionSummary
from ..security import get_current_user

router = APIRouter(prefix="/api/questions", tags=["questions"])


def _summary(q: Question) -> QuestionSummary:
    return QuestionSummary(
        id=q.id, title=q.title, interview_type=q.interview_type,
        category=q.category, difficulty=q.difficulty,
        prompt_preview=q.prompt[:220] + ("…" if len(q.prompt) > 220 else ""),
        custom=q.status == "custom",
    )


@router.get("", response_model=list[QuestionSummary])
def list_questions(
    interview_type: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionSummary]:
    stmt = select(Question).where(Question.status.in_(["active", "custom"]))
    if interview_type:
        stmt = stmt.where(Question.interview_type == interview_type)
    if category:
        stmt = stmt.where(Question.category == category)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    questions = db.scalars(stmt.order_by(Question.category, Question.difficulty, Question.title))
    return [_summary(q) for q in questions]


@router.post("/custom", response_model=QuestionSummary, status_code=http_status.HTTP_201_CREATED)
def create_custom_question(
    body: CustomQuestionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionSummary:
    """User-written question. status='custom' keeps it out of the random
    planner pool — it is used explicitly (interview / lesson / duo watch)."""
    q = Question(
        interview_type=body.interview_type, category="custom",
        difficulty=body.difficulty, title=body.title.strip(),
        prompt=body.prompt.strip(), examples=[], constraints=[],
        test_cases=[], rubric={"expected": []}, status="custom",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return _summary(q)
