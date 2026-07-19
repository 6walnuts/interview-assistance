from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import InterviewMessage, InterviewReport, InterviewSession, Question, ReviewTask, User
from ..schemas import (
    EndInterviewRequest,
    EndInterviewResponse,
    ExecutionOut,
    InterviewCreate,
    InterviewCreateResponse,
    InterviewDetail,
    MessageOut,
    QuestionOut,
    ReportOut,
    ReviewTaskOut,
    RunCodeRequest,
    RunCodeResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionOut,
    TestResultOut,
)
from ..security import get_current_user
from ..services import interview_service

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _session_out(s: InterviewSession) -> SessionOut:
    return SessionOut(
        id=s.id, interview_type=s.interview_type, role=s.role, level=s.level,
        company_style=s.company_style, duration_minutes=s.duration_minutes,
        difficulty=s.difficulty, language=s.language, current_stage=s.current_stage,
        status=s.status, started_at=s.started_at, ended_at=s.ended_at,
    )


def _question_out(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, title=q.title, prompt=q.prompt, examples=q.examples,
                       constraints=q.constraints, difficulty=q.difficulty)


def _message_out(m: InterviewMessage) -> MessageOut:
    # internal_observation is intentionally never serialized.
    return MessageOut(id=m.id, role=m.role, content=m.content, stage=m.stage, created_at=m.created_at)


def _owned_session(session_id: str, user: User, db: Session) -> InterviewSession:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if session.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your interview")
    return session


def _require_in_progress(session: InterviewSession) -> None:
    if session.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "Interview already ended")


@router.post("", response_model=InterviewCreateResponse, status_code=status.HTTP_201_CREATED)
def create_interview(
    body: InterviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> InterviewCreateResponse:
    try:
        session, question, opening = interview_service.create_session(db, user, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return InterviewCreateResponse(
        session=_session_out(session), question=_question_out(question),
        opening_message=_message_out(opening),
    )


@router.get("/{session_id}", response_model=InterviewDetail)
def get_interview(
    session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> InterviewDetail:
    session = _owned_session(session_id, user, db)
    return InterviewDetail(
        session=_session_out(session),
        question=_question_out(session.question) if session.question else None,
        # system messages carry interviewer-private notes (voice stage changes,
        # observations) — never exposed, like internal_observation itself.
        messages=[_message_out(m) for m in session.messages if m.role != "system"],
    )


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str, body: SendMessageRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> SendMessageResponse:
    session = _owned_session(session_id, user, db)
    _require_in_progress(session)
    reply = interview_service.handle_candidate_message(db, session, body.content, body.action)
    return SendMessageResponse(message=_message_out(reply), current_stage=session.current_stage)


@router.post("/{session_id}/run-code", response_model=RunCodeResponse)
def run_code(
    session_id: str, body: RunCodeRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> RunCodeResponse:
    session = _owned_session(session_id, user, db)
    _require_in_progress(session)
    if session.interview_type != "coding":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Code execution is only available in coding interviews")
    result = interview_service.run_code(db, session, body.code, body.language, body.label)
    return RunCodeResponse(execution=ExecutionOut(
        stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code,
        timed_out=result.timed_out, duration_ms=result.duration_ms,
        test_results=[TestResultOut(**t) for t in result.test_results],
    ))


@router.post("/{session_id}/end", response_model=EndInterviewResponse)
def end_interview(
    session_id: str, body: EndInterviewRequest | None = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> EndInterviewResponse:
    session = _owned_session(session_id, user, db)
    generate = body.generate_report if body is not None else True
    report, task_count = interview_service.end_interview(db, session, generate_report=generate)
    return EndInterviewResponse(report_id=report.id if report else None,
                                review_task_count=task_count)


@router.get("/{session_id}/report", response_model=ReportOut)
def get_report(
    session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ReportOut:
    session = _owned_session(session_id, user, db)
    report = db.scalars(select(InterviewReport).where(InterviewReport.session_id == session.id)).first()
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not generated yet")
    return ReportOut(
        session_id=session.id, interview_summary=report.interview_summary,
        overall_score=report.overall_score, hire_signal=report.hire_signal,
        level_assessment=report.level_assessment, scores=report.scores,
        strengths=report.strengths, weaknesses=report.weaknesses,
        key_mistakes=report.key_mistakes, missed_opportunities=report.missed_opportunities,
        hints_used=report.hints_used, evidence=report.evidence,
        ideal_answer_outline=report.ideal_answer_outline,
        recommended_practice=report.recommended_practice,
        next_interview_focus=report.next_interview_focus,
    )


@router.get("/{session_id}/review-tasks", response_model=list[ReviewTaskOut])
def get_review_tasks(
    session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ReviewTaskOut]:
    session = _owned_session(session_id, user, db)
    tasks = db.scalars(select(ReviewTask).where(ReviewTask.session_id == session.id))
    return [ReviewTaskOut(id=t.id, diagnosed_weakness=t.diagnosed_weakness, topic_slug=t.topic_slug,
                          task_type=t.task_type, title=t.title, description=t.description,
                          status=t.status) for t in tasks]
