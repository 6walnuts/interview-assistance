"""Thin multi-provider LLM wrapper. Every agent calls `complete_json(...)`.

Providers (LLM_PROVIDER):
  - "openai"    OpenAI API (default)
  - "deepseek"  DeepSeek — OpenAI-compatible endpoint
  - "kimi"      Moonshot/Kimi — OpenAI-compatible endpoint
  - "anthropic" Claude — official Anthropic SDK

All output is validated against a Pydantic schema; a malformed response is
retried once with the validation error before raising AgentError. When AI is
disabled (no key or MOCK_AI=true) the deterministic mock_factory result is
returned instead, so the entire product loop runs offline/in tests.
"""
import json
import logging
import re
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

RETRY_PROMPT = (
    "Your previous output was invalid JSON for the required schema: {error}. "
    "Reply again with ONLY valid JSON matching the schema."
)


class AgentError(RuntimeError):
    pass


def _parse(raw: str, schema: type[T]) -> T:
    # Tolerate markdown fences some models wrap around JSON.
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text).strip()
    return schema.model_validate(json.loads(text))


def complete_json(
    system: str,
    messages: list[dict[str, str]],
    schema: type[T],
    mock_factory: Callable[[], T],
) -> T:
    settings = get_settings()
    if not settings.ai_enabled:
        return mock_factory()
    if settings.llm_provider == "anthropic":
        return _complete_anthropic(system, messages, schema)
    return _complete_openai_compatible(system, messages, schema)


def _complete_openai_compatible(system: str, messages: list[dict], schema: type[T]) -> T:
    from openai import OpenAI  # lazy import: mock mode needs no SDK

    settings = get_settings()
    client = OpenAI(api_key=settings.resolved_api_key, base_url=settings.resolved_base_url)
    chat = [{"role": "system", "content": system}, *messages]

    last_error: Exception | None = None
    for attempt in range(2):
        response = client.chat.completions.create(
            model=settings.resolved_model,
            messages=chat,
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return _parse(raw, schema)
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("LLM output failed validation (attempt %d): %s", attempt + 1, exc)
            chat += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": RETRY_PROMPT.format(error=exc)}]
    raise AgentError(f"LLM output failed schema validation after retry: {last_error}")


def _complete_anthropic(system: str, messages: list[dict], schema: type[T]) -> T:
    import anthropic  # lazy import: only needed for this provider

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.resolved_api_key)

    chat = [dict(m) for m in messages]
    # The Messages API requires the first message to be from the user; our
    # interview transcripts can start with the interviewer (assistant).
    if not chat or chat[0]["role"] != "user":
        chat.insert(0, {"role": "user", "content": "[The session begins.]"})

    last_error: Exception | None = None
    for attempt in range(2):
        response = client.messages.create(
            model=settings.resolved_model,
            max_tokens=16000,
            system=system,
            messages=chat,
        )
        if response.stop_reason == "refusal":
            raise AgentError("The model declined this request (stop_reason=refusal).")
        raw = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return _parse(raw, schema)
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("LLM output failed validation (attempt %d): %s", attempt + 1, exc)
            chat += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": RETRY_PROMPT.format(error=exc)}]
    raise AgentError(f"LLM output failed schema validation after retry: {last_error}")
