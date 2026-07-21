"""Interview Coach Agent: teaching, never examining."""
import json
import re

from ..models import Question, UserProfile, UserSkillProfile
from .agent_schemas import CoachReply
from .llm import complete_json, stream_reply
from .prompts import (
    BQ_DUO_ANSWERER_SYSTEM,
    BQ_DUO_ASKER_SYSTEM,
    COACH_SYSTEM,
    DUO_ANSWERER_SYSTEM,
    DUO_ASKER_SYSTEM,
    DUO_SD_ANSWERER_SYSTEM,
    DUO_SD_ASKER_SYSTEM,
    TUTOR_SYSTEM,
    language_instruction,
)

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


def _mock_reply(mode: str, topic: str, message: str = "", hist_len: int = 0) -> CoachReply:
    if mode in ("duo_asker", "bq_asker"):
        n = hist_len // 2 + 1
        if n > 5:  # deterministic wrap-up so the end-of-dialogue flow is testable
            return CoachReply(
                reply="(mock closing) Credible: the rollback story. Would not survive a "
                      "reference check: the unquantified 'improved reliability' claim. "
                      "[END_OF_DIALOGUE]",
            )
        if mode == "bq_asker":
            return CoachReply(
                reply=f"(mock BQ interviewer) Question {n}: tell me about a time on the "
                      f"project from your resume when things went wrong — what exactly "
                      f"did YOU do, and what was the measurable result?",
            )
        return CoachReply(
            reply=f"(mock asker) Question {n} on {topic}: explain the core mechanism "
                  f"at depth level {n}, and where does it break down?",
        )
    if mode == "bq_answerer":
        return CoachReply(
            reply="(mock candidate) At that point our launch was slipping; I owned the "
                  "rollback plan, drove the fix across two teams, and we shipped 3 days "
                  "late instead of 3 weeks — the lesson was to cut scope earlier.",
        )
    if mode == "duo_answerer":
        # Whiteboard grows deterministically with dialogue depth.
        n = hist_len // 2 + 1
        board = "\n".join(["[client] -> [api]"] +
                          [f"[api] -> [component-{i}]" for i in range(1, n + 1)])
        return CoachReply(
            reply=f"(mock answerer) Model answer on {topic}: the mechanism works like X, "
                  f"the tradeoff interviewers listen for is Y, and a concrete example is Z.",
            code_snippet=board,
        )
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


def _is_design_context(question: Question | None, topic_category: str | None) -> bool:
    """Design-interview style duos: anchored on a system_design question, or
    running on a topic from the system-design category."""
    if question is not None and question.interview_type == "system_design":
        return True
    return topic_category == "system_design"


def _build_prompt(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None,
    question: Question | None = None,
    topic_category: str | None = None,
) -> tuple[str, list[dict[str, str]], str]:
    topic = topic_slug or "general interview preparation"
    skill_state = (
        {"skill_level": skill.skill_level, "mastery_score": skill.mastery_score,
         "common_mistakes": skill.common_mistakes}
        if skill else {"skill_level": 0, "mastery_score": 0, "common_mistakes": []}
    )
    locale = profile.locale if profile else "en"
    level = profile.target_level if profile else "mid"
    role = profile.target_role if profile else "Software Engineer"
    if mode == "lesson":
        base = TUTOR_SYSTEM.format(level=level, role=role, topic=topic,
                                   skill_state=json.dumps(skill_state))
    elif mode == "duo_asker":
        template = (DUO_SD_ASKER_SYSTEM if _is_design_context(question, topic_category)
                    else DUO_ASKER_SYSTEM)
        base = template.format(level=level, role=role, topic=topic)
    elif mode == "duo_answerer":
        template = (DUO_SD_ANSWERER_SYSTEM if _is_design_context(question, topic_category)
                    else DUO_ANSWERER_SYSTEM)
        base = template.format(level=level, role=role, topic=topic)
    elif mode in ("bq_asker", "bq_answerer"):
        resume = ((profile.resume_text or "").strip()[:4000] if profile else "") or "(empty)"
        jd = ((profile.target_jd or "").strip()[:3000] if profile else "") or "(empty)"
        template = BQ_DUO_ASKER_SYSTEM if mode == "bq_asker" else BQ_DUO_ANSWERER_SYSTEM
        base = template.format(level=level, role=role, resume=resume, jd=jd)
    if mode in ("duo_asker", "bq_asker"):
        # Models are unreliable at counting their own turns — inject the
        # count server-side so pacing and termination actually happen.
        asked = len(history or []) // 2
        base += (
            f"\nProgress: you have already asked {asked} questions.\n"
            "Hard pacing rules: never spend more than 2 consecutive follow-ups "
            "on the same story — after two, you MUST move to a completely new "
            "theme or resume item, even if the last answer was still weak "
            "(note the weakness for your closing assessment instead). "
        )
        if asked >= 9:
            base += (
                "You have reached the question budget: THIS turn must be the "
                "closing assessment and MUST end with [END_OF_DIALOGUE]. "
                "Do not ask another question.\n"
            )
    else:
        base = COACH_SYSTEM.format(level=level, role=role, mode=mode, topic=topic,
                                   skill_state=json.dumps(skill_state))
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
    topic_category: str | None = None,
) -> CoachReply:
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill,
                                            history, question, topic_category)
    n = len(history or [])
    return _hoist_code(complete_json(system, messages, CoachReply,
                                     lambda: _mock_reply(mode, topic, message, n)))


def chat_stream(
    message: str,
    mode: str,
    topic_slug: str | None,
    profile: UserProfile | None,
    skill: UserSkillProfile | None,
    history: list[dict[str, str]] | None = None,
    question: Question | None = None,
    topic_category: str | None = None,
):
    """Yields ("delta", text) chunks then ("final", CoachReply)."""
    system, messages, topic = _build_prompt(message, mode, topic_slug, profile, skill,
                                            history, question, topic_category)
    n = len(history or [])
    for kind, payload in stream_reply(system, messages, CoachReply,
                                      lambda: _mock_reply(mode, topic, message, n)):
        # The final payload replaces the streamed bubble, so fence cleanup
        # lands even though deltas may have shown raw markdown briefly.
        yield (kind, _hoist_code(payload) if kind == "final" else payload)
