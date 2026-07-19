"""Mock Interviewer Agent: one turn per candidate message, stage-machine driven."""
from ..models import InterviewSession, Question
from .agent_schemas import InternalObservation, InterviewerTurn, Stage
from .llm import complete_json
from .prompts import INTERVIEWER_SYSTEM, language_instruction

STAGES: list[Stage] = [
    "introduction", "question_presentation", "clarification", "approach",
    "deep_dive", "coding", "testing", "complexity", "optimization",
    "follow_up", "candidate_questions", "finish",
]

_MOCK_LINES: dict[str, str] = {
    "introduction": "Hi, thanks for joining. I'm your interviewer today. "
                    "We'll spend most of the time on one problem. Ready to start?",
    "question_presentation": "Here's the problem — take a moment to read it, and let me know "
                             "if anything needs clarifying before you dive in.",
    "clarification": "Good questions. Assume inputs fit in memory and focus on correctness first.",
    "approach": "Before you write any code, walk me through your approach.",
    "deep_dive": "Why did you choose that data structure? What's the tradeoff?",
    "coding": "Sounds reasonable. Go ahead and implement it.",
    "testing": "How would you test this? Walk me through your edge cases.",
    "complexity": "What's the time and space complexity of your solution?",
    "optimization": "Can you do better? Where's the bottleneck?",
    "follow_up": "Suppose the input no longer fits in memory — how does your approach change?",
    "candidate_questions": "That's all from my side. Do you have any questions for me?",
    "finish": "Thanks for your time today — that wraps up the interview. "
              "Your report will be ready shortly.",
}


def _mock_turn(session: InterviewSession, action: str) -> InterviewerTurn:
    current = session.current_stage if session.current_stage in STAGES else "introduction"
    idx = STAGES.index(current)
    if action == "request_hint":
        level = min(session.hint_count + 1, 3)
        return InterviewerTurn(
            message="I won't give it away, but consider what happens at the boundaries of "
                    "your input — what case are you not handling yet?",
            stage=current,  # hints do not advance the stage
            hint_content=(
                "# Hint skeleton (mock)\n"
                "def solve(data):\n"
                "    # TODO: handle the empty input case first\n"
                "    # TODO: what happens at the last element?\n"
                "    ...\n"),
            internal_observation=InternalObservation(
                candidate_signal="asked for a hint", hint_level=level,
                recommended_follow_up="check if the hint unblocks them"),
        )
    next_stage: Stage = STAGES[min(idx + 1, len(STAGES) - 1)]
    return InterviewerTurn(
        message=_MOCK_LINES[next_stage],
        stage=next_stage,
        action="end_interview" if next_stage == "finish" else "wait_for_candidate",
        internal_observation=InternalObservation(
            candidate_signal=f"progressed to {next_stage}",
            recommended_follow_up="probe the weakest part of the last answer"),
    )


def _format_question(question: Question | None) -> str:
    if question is None:
        return "(no question attached)"
    parts = [f"Title: {question.title}", f"Prompt: {question.prompt}"]
    if question.constraints:
        parts.append(f"Constraints: {question.constraints}")
    return "\n".join(parts)


def next_turn(
    session: InterviewSession,
    question: Question | None,
    transcript: list[dict[str, str]],
    action: str = "message",
    execution_summary: str = "",
    locale: str = "en",
    resume: str = "",
) -> InterviewerTurn:
    """transcript: [{"role": "interviewer"|"candidate", "content": ...}] oldest first."""
    system = language_instruction(locale) + INTERVIEWER_SYSTEM.format(
        company_style=session.company_style,
        level=session.level,
        role=session.role,
        interview_type=session.interview_type,
        question=_format_question(question),
        resume=resume or "(none provided)",
        current_stage=session.current_stage,
        hint_count=session.hint_count,
        execution_summary=execution_summary or "(none)",
    )
    messages = [
        {"role": "assistant" if m["role"] == "interviewer" else "user", "content": m["content"]}
        for m in transcript
    ]
    if action == "request_hint":
        messages.append({"role": "user", "content": "[The candidate pressed the Request Hint button.]"})
    return complete_json(system, messages, InterviewerTurn, lambda: _mock_turn(session, action))
