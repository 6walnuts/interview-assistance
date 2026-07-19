from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import quiz_gen
from ..db import get_db
from ..models import LearningTask, LearningTopic, QuizAttempt, QuizQuestion, User, UserProfile, UserSkillProfile
from ..schemas import (
    QuizOut,
    QuizQuestionOut,
    QuizResultItem,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from ..security import get_current_user

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

PASS_RATIO = 0.6  # quizzes at or above this auto-complete matching learning tasks


def _topic_by_slug(db: Session, slug: str) -> LearningTopic:
    topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == slug)).first()
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    return topic


@router.get("/{topic_slug}", response_model=QuizOut)
def get_quiz(
    topic_slug: str,
    count: int = Query(default=5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizOut:
    topic = _topic_by_slug(db, topic_slug)
    questions = list(db.scalars(select(QuizQuestion).where(
        QuizQuestion.topic_id == topic.id, QuizQuestion.status == "active")))

    if len(questions) < count:  # top up the bank via the quiz generator
        profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
        generated = quiz_gen.generate_quiz(
            topic, count - len(questions), [q.question for q in questions], profile)
        for g in generated.questions:
            q = QuizQuestion(topic_id=topic.id, question=g.question, options=g.options,
                             answer_index=g.answer_index, explanation=g.explanation,
                             difficulty=g.difficulty)
            db.add(q)
            questions.append(q)
        db.commit()

    picked = questions[:count]
    return QuizOut(
        topic_id=topic.id, topic_slug=topic.slug, topic_name=topic.name,
        questions=[QuizQuestionOut(id=q.id, question=q.question, options=q.options,
                                   difficulty=q.difficulty) for q in picked],
    )


@router.post("/{topic_slug}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    topic_slug: str,
    body: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizSubmitResponse:
    topic = _topic_by_slug(db, topic_slug)
    now = datetime.now(timezone.utc)

    results: list[QuizResultItem] = []
    correct = 0
    mistakes: list[str] = []
    for answer in body.answers:
        question = db.get(QuizQuestion, answer.question_id)
        if question is None or question.topic_id != topic.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"Question {answer.question_id} does not belong to this quiz")
        is_correct = answer.selected_index == question.answer_index
        correct += is_correct
        if not is_correct:
            mistakes.append(question.question[:120])
        db.add(QuizAttempt(user_id=user.id, quiz_question_id=question.id,
                           selected_index=answer.selected_index, is_correct=is_correct))
        results.append(QuizResultItem(
            question_id=question.id, question=question.question, options=question.options,
            selected_index=answer.selected_index, correct_index=question.answer_index,
            is_correct=is_correct, explanation=question.explanation))

    total = len(body.answers)
    wrong = total - correct

    skill = db.scalars(select(UserSkillProfile).where(
        UserSkillProfile.user_id == user.id, UserSkillProfile.topic_id == topic.id)).first()
    if skill is None:
        skill = UserSkillProfile(user_id=user.id, topic_id=topic.id)
        db.add(skill)
        db.flush()
    skill.correct_answers = (skill.correct_answers or 0) + correct
    skill.incorrect_answers = (skill.incorrect_answers or 0) + wrong
    skill.mastery_score = max(0, min(100, (skill.mastery_score or 0) + 4 * correct - 2 * wrong))
    skill.skill_level = min(5, skill.mastery_score // 20)
    skill.common_mistakes = list(dict.fromkeys([*(skill.common_mistakes or []), *mistakes]))[-10:]
    skill.last_practiced_at = now

    # Passing the quiz closes any matching pending learning tasks.
    completed_ids: list[str] = []
    if total and correct / total >= PASS_RATIO:
        pending = db.scalars(select(LearningTask).where(
            LearningTask.user_id == user.id, LearningTask.status == "pending",
            LearningTask.task_type == "quiz", LearningTask.topic_slug == topic.slug))
        for task in pending:
            task.status = "completed"
            task.completed_at = now
            completed_ids.append(task.id)

    db.commit()
    return QuizSubmitResponse(
        correct=correct, total=total, mastery_score=skill.mastery_score,
        skill_level=skill.skill_level, completed_task_ids=completed_ids, results=results)
