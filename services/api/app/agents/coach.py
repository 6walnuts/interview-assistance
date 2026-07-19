"""Interview Coach Agent: teaching, never examining."""
import json
import re

from ..models import Question, UserProfile, UserSkillProfile
from .agent_schemas import CoachReply
from .llm import complete_json, stream_reply
from .prompts import COACH_SYSTEM, TUTOR_SYSTEM, language_instruction

# A language tag only counts as such when a newline follows the opening fence
# (otherwise "```x = 1```" would lose its first token).
_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+#-]*\n)?(.*?)```", re.DOTALL)


def _hoist_code(reply: CoachReply) -> CoachReply:
    """Models sometimes put code in the chat text instead of code_snippet.
    Move the largest fenced block into code_snippet (when it's empty) and
    strip fence markers from the prose so the chat never shows raw ```."""
    blocks = _FENCE_RE.findall(reply.reply)
    if not blocks:
        return reply
    if not reply.code_snippet.strip():
        hoisted = max(blocks, key=len)
        reply.code_snippet = hoisted.strip("\n")
        # Remove the hoisted block from the prose entirely (it now lives in
        # the editor panel); unfence any remaining smaller blocks.
        reply.reply = _FENCE_RE.sub(
            lambda m: "" if m.group(1) == hoisted else m.group(1), reply.reply)
    else:
        reply.reply = _FENCE_RE.sub(lambda m: m.group(1), reply.reply)
    reply.reply = re.sub(r"\n{3,}", "\n\n", reply.reply).strip()
    return reply


def _mock_reply(mode: str, topic: str, message: str = "") -> CoachReply:
    snippet = ""
    if "hint" in message.lower():
        snippet = (
            "# Hint skeleton (mock)\n"
            "def attempt(data):\n"
            "    # TODO: start from the simplest case\n"
            "    ...\n")
    return CoachReply(
        reply=f"(mock coach, mode={mode}) Let's work on {topic}. Start by telling me, "
              f"in your own words, what you already know about it — then I'll fill the gaps "
              f"and quiz you on the parts interviewers care about.",
        suggested_actions=[f"Take the {topic} quiz", f"Review common {topic} mistakes",
                           "Generate a daily plan"],
        code_snippet=snippet,
    )


def _build_prompt(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None,
    question: Question | None = None,
) -> tuple[str, list[dict[str, str]], str]:
    topic = topic_slug or "general interview preparation"
    skill_state = (
        {"skill_level": skill.skill_level, "mastery_score": skill.mastery_score,
         "common_mistakes": skill.common_mistakes}
        if skill else {"skill_level": 0, "mastery_score": 0, "common_mistakes": []}
    )
    locale = profile.locale if profile else "en"
    if mode == "lesson":
        base = TUTOR_SYSTEM.format(
            level=profile.target_level if profile else "mid",
            role=profile.target_role if profile else "Software Engineer",
            topic=topic, skill_state=json.dumps(skill_state),
        )
    else:
        base = COACH_SYSTEM.format(
            level=profile.target_level if profile else "mid",
            role=profile.target_role if profile else "Software Engineer",
            mode=mode, topic=topic, skill_state=json.dumps(skill_state),
        )
    if question is not None:
        base += (
            "\nThis lesson is anchored on one classic interview question — teach the "
            "student to master it step by step, working through the evaluation points:\n"
            f"Title: {question.title}\nPrompt: {question.prompt}\n"
            f"Evaluation points: {json.dumps(question.rubric.get('expected', []))}\n"
        )
    system = language_instruction(locale) + base
    messages = [*(history or []), {"role": "user", "content": message}]
    return system, messages, topic


def chat(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None = None,
    question: Question | None = None,
) -> CoachReply:
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill,
                                            history, question)
    return _hoist_code(complete_json(system, messages, CoachReply,
                                     lambda: _mock_reply(mode, topic, message)))


def chat_stream(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None = None,
    question: Question | None = None,
):
    """Yields ("delta", text) chunks then ("final", CoachReply)."""
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill,
                                            history, question)
    for kind, payload in stream_reply(system, messages, CoachReply,
                                      lambda: _mock_reply(mode, topic, message)):
        # The final payload replaces the streamed bubble, so fence cleanup
        # lands even though deltas may have shown raw markdown briefly.
        yield (kind, _hoist_code(payload) if kind == "final" else payload)
