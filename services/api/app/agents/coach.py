"""Interview Coach Agent: teaching, never examining."""
import json

from ..models import UserProfile, UserSkillProfile
from .agent_schemas import CoachReply
from .llm import complete_json, stream_reply
from .prompts import COACH_SYSTEM, TUTOR_SYSTEM, language_instruction


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
) -> CoachReply:
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill, history)
    return complete_json(system, messages, CoachReply,
                         lambda: _mock_reply(mode, topic, message))


def chat_stream(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None = None,
):
    """Yields ("delta", text) chunks then ("final", CoachReply)."""
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill, history)
    yield from stream_reply(system, messages, CoachReply,
                            lambda: _mock_reply(mode, topic, message))
