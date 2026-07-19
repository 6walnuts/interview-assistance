"""Interview Planner Agent: selects the question + rubric for a new session.

MVP: deterministic selection from the question bank (type + difficulty +
focus-area match, least-recently-used for this user). An LLM is intentionally
NOT required here — selection is a ranking problem over structured data.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import InterviewSession, Question


def pick_question(db: Session, *, interview_type: str, difficulty: str,
                  focus_areas: list[str], user_id: str) -> Question | None:
    candidates = list(db.scalars(
        select(Question).where(
            Question.interview_type == interview_type,
            Question.status == "active",
        )
    ))
    if not candidates:
        return None

    used_ids = set(db.scalars(
        select(InterviewSession.question_id).where(InterviewSession.user_id == user_id)
    ))
    focus = {f.lower() for f in focus_areas}

    def rank(q: Question) -> tuple:
        return (
            q.id in used_ids,                      # unseen questions first
            q.difficulty != difficulty,            # requested difficulty first
            not (focus and q.category.lower() in focus),  # focus-area match first
        )

    return sorted(candidates, key=rank)[0]
