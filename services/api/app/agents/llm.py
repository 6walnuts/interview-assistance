"""Thin LLM wrapper: OpenAI structured JSON output, validated by Pydantic.

Every agent calls `complete_json(system, messages, schema, mock_factory)`.
When AI is disabled (no key or MOCK_AI=true) the deterministic mock_factory
result is returned instead, so the entire product loop runs offline/in tests.
A malformed model response is retried once before raising AgentError.
"""
import json
import logging
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AgentError(RuntimeError):
    pass


def complete_json(
    system: str,
    messages: list[dict[str, str]],
    schema: type[T],
    mock_factory: Callable[[], T],
) -> T:
    settings = get_settings()
    if not settings.ai_enabled:
        return mock_factory()

    from openai import OpenAI  # imported lazily so mock mode needs no SDK

    client = OpenAI(api_key=settings.openai_api_key)
    chat = [{"role": "system", "content": system}, *messages]

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=chat,
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            raw = response.choices[0].message.content or "{}"
            return schema.model_validate(json.loads(raw))
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Agent output failed validation (attempt %d): %s", attempt + 1, exc)
            chat.append({
                "role": "user",
                "content": f"Your previous output was invalid JSON for the required schema: {exc}. "
                           f"Reply again with ONLY valid JSON matching the schema.",
            })
    raise AgentError(f"LLM output failed schema validation after retry: {last_error}")
