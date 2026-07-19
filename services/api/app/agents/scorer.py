"""Scoring Agent: independent post-interview evaluation. Never the interviewer."""
import json

from ..models import InterviewSession, Question
from .agent_schemas import ScoringReport
from .llm import complete_json
from .prompts import DIMENSIONS_BY_TYPE, SCORER_SYSTEM, language_instruction


def _mock_report(session: InterviewSession, tests_passed: bool, hint_count: int) -> ScoringReport:
    dims = DIMENSIONS_BY_TYPE[session.interview_type]
    base = 3 if tests_passed else 2
    scores = {d: base for d in dims}
    if hint_count:
        for d in ("problem_solving", "requirements_clarification"):
            if d in scores:
                scores[d] = max(1, scores[d] - 1)
    overall = round(sum(scores.values()) / len(scores), 1)
    return ScoringReport(
        interview_summary=f"Mock evaluation of a {session.level} {session.role} "
                          f"{session.interview_type} interview.",
        overall_score=overall,
        hire_signal="lean_hire" if tests_passed and not hint_count else "mixed",
        level_assessment=f"Around {session.level} bar" if tests_passed else f"Below {session.level} bar",
        scores=scores,
        strengths=["Communicated the approach before coding"],
        weaknesses=["Did not proactively test edge cases",
                    "Did not discuss idempotency / failure handling"],
        key_mistakes=[] if tests_passed else ["Final solution failed one or more test cases"],
        missed_opportunities=["Could have discussed a more optimal approach unprompted"],
        hints_used=[f"hint #{i + 1}" for i in range(hint_count)],
        evidence=["(mock mode: evidence synthesis disabled)"],
        ideal_answer_outline=["Clarify constraints", "State brute force + complexity",
                              "Derive optimal approach", "Implement cleanly",
                              "Test edge cases", "Analyze complexity"],
        recommended_practice=["edge-case testing drills", "complexity analysis quiz"],
        next_interview_focus=["testing discipline", "optimization discussion"],
    )


def score_interview(
    session: InterviewSession,
    question: Question | None,
    transcript: list[dict[str, str]],
    code_versions: list[dict],
    execution_results: list[dict],
    internal_observations: list[dict],
    locale: str = "en",
) -> ScoringReport:
    dims = DIMENSIONS_BY_TYPE[session.interview_type]
    system = language_instruction(locale) + SCORER_SYSTEM.format(
        level=session.level, role=session.role,
        interview_type=session.interview_type, dimensions=", ".join(dims),
    )
    payload = {
        "question": {"title": question.title, "prompt": question.prompt,
                     "rubric": question.rubric} if question else None,
        "transcript": transcript,
        "code_versions": code_versions,
        "execution_results": execution_results,
        "hints_used_count": session.hint_count,
        "duration_minutes": session.duration_minutes,
        "interviewer_internal_observations": internal_observations,
    }
    tests_passed = all(
        t.get("passed") for r in execution_results for t in r.get("test_results", [])
    ) and any(r.get("test_results") for r in execution_results)
    messages = [{"role": "user", "content": json.dumps(payload, default=str)}]
    return complete_json(
        system, messages, ScoringReport,
        lambda: _mock_report(session, tests_passed, session.hint_count),
    )
