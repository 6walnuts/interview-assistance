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
    """LLM provider call failed; message is safe to surface to the user."""


def _validated_api_key(settings) -> str:
    key = settings.resolved_api_key.strip()
    if not key.isascii():
        raise AgentError(
            "LLM_API_KEY 含有非 ASCII 字符——多半是复制粘贴时混入了全角字符、"
            "中文标点或不可见字符。请删掉 .env 中该行，切换到英文输入法后重新粘贴。")
    return key


def _friendly_provider_error(exc: Exception, provider: str) -> "AgentError":
    text = str(exc)
    if "insufficient_quota" in text or "exceeded your current quota" in text:
        return AgentError(
            f"你的 {provider} 账户余额不足（insufficient_quota）。请到该平台充值，"
            f"或改用其他 LLM_PROVIDER。")
    if "invalid_api_key" in text or "Incorrect API key" in text or "authentication" in text.lower():
        return AgentError(f"{provider} API key 无效，请检查 LLM_API_KEY 配置。")
    if "rate_limit" in text or "429" in text:
        return AgentError(f"{provider} 请求频率超限，请稍后重试。")
    return AgentError(f"{provider} 调用失败：{text[:300]}")


def _parse(raw: str, schema: type[T]) -> T:
    # Tolerate markdown fences some models wrap around JSON.
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text).strip()
    return schema.model_validate(json.loads(text))


_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
            "n": "\n", "r": "\r", "t": "\t"}


class _ReplyFieldExtractor:
    """Incrementally decodes the string value of one field from a streamed
    JSON object, so the reply can be forwarded token-by-token while the rest
    of the JSON (actions, snippets) is parsed once the stream completes.
    Handles escape sequences split across chunk boundaries."""

    def __init__(self, field: str):
        self._marker = re.compile(r'"%s"\s*:\s*"' % re.escape(field))
        self.raw = ""
        self._start: int | None = None
        self._pos = 0
        self._escape = ""
        self.done = False

    def feed(self, chunk: str) -> str:
        self.raw += chunk
        if self.done:
            return ""
        if self._start is None:
            m = self._marker.search(self.raw)
            if not m:
                return ""
            self._start = self._pos = m.end()
        out: list[str] = []
        s = self.raw
        i = self._pos
        while i < len(s):
            c = s[i]
            if self._escape:
                self._escape += c
                if self._escape[1] == "u":
                    if len(self._escape) == 6:
                        try:
                            out.append(chr(int(self._escape[2:], 16)))
                        except ValueError:
                            pass
                        self._escape = ""
                else:
                    out.append(_ESCAPES.get(self._escape[1], self._escape[1]))
                    self._escape = ""
            elif c == "\\":
                self._escape = "\\"
            elif c == '"':
                self.done = True
                i += 1
                break
            else:
                out.append(c)
            i += 1
        self._pos = i
        return "".join(out)


def stream_reply(
    system: str,
    messages: list[dict[str, str]],
    schema: type[T],
    mock_factory: Callable[[], T],
    reply_field: str = "reply",
):
    """Yield ("delta", text) chunks of the reply field as the model streams,
    then ("final", validated_schema_instance). If the completed JSON fails
    validation, the final falls back to a reply-only instance so the user
    still gets the streamed text."""
    settings = get_settings()
    if not settings.ai_enabled:
        mock = mock_factory()
        text = getattr(mock, reply_field)
        for i in range(0, len(text), 24):
            yield ("delta", text[i:i + 24])
        yield ("final", mock)
        return
    if settings.llm_provider == "anthropic":
        yield from _stream_anthropic(system, messages, schema, reply_field)
    else:
        yield from _stream_openai_compatible(system, messages, schema, reply_field)


def _finalize_stream(extractor: _ReplyFieldExtractor, decoded: str,
                     schema: type[T], reply_field: str) -> T:
    try:
        return _parse(extractor.raw, schema)
    except (ValidationError, json.JSONDecodeError):
        logger.warning("Streamed output failed validation; falling back to reply-only")
        return schema(**{reply_field: decoded})


def _stream_openai_compatible(system: str, messages: list[dict], schema: type[T],
                              reply_field: str):
    from openai import OpenAI, OpenAIError

    settings = get_settings()
    client = OpenAI(api_key=_validated_api_key(settings), base_url=settings.resolved_base_url)
    extractor = _ReplyFieldExtractor(reply_field)
    decoded: list[str] = []
    try:
        stream = client.chat.completions.create(
            model=settings.resolved_model,
            messages=[{"role": "system", "content": system}, *messages],
            response_format={"type": "json_object"},
            temperature=0.4,
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                text = extractor.feed(delta)
                if text:
                    decoded.append(text)
                    yield ("delta", text)
    except OpenAIError as exc:
        raise _friendly_provider_error(exc, settings.llm_provider) from exc
    yield ("final", _finalize_stream(extractor, "".join(decoded), schema, reply_field))


def _stream_anthropic(system: str, messages: list[dict], schema: type[T], reply_field: str):
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic(api_key=_validated_api_key(settings))
    chat = [dict(m) for m in messages]
    if not chat or chat[0]["role"] != "user":
        chat.insert(0, {"role": "user", "content": "[The session begins.]"})
    extractor = _ReplyFieldExtractor(reply_field)
    decoded: list[str] = []
    try:
        with client.messages.stream(
            model=settings.resolved_model, max_tokens=16000, system=system, messages=chat,
        ) as stream:
            for text_chunk in stream.text_stream:
                text = extractor.feed(text_chunk)
                if text:
                    decoded.append(text)
                    yield ("delta", text)
    except anthropic.AnthropicError as exc:
        raise _friendly_provider_error(exc, "anthropic") from exc
    yield ("final", _finalize_stream(extractor, "".join(decoded), schema, reply_field))


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
    client = OpenAI(api_key=_validated_api_key(settings), base_url=settings.resolved_base_url)
    chat = [{"role": "system", "content": system}, *messages]

    from openai import OpenAIError

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.resolved_model,
                messages=chat,
                response_format={"type": "json_object"},
                temperature=0.4,
            )
        except OpenAIError as exc:
            raise _friendly_provider_error(exc, settings.llm_provider) from exc
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
    client = anthropic.Anthropic(api_key=_validated_api_key(settings))

    chat = [dict(m) for m in messages]
    # The Messages API requires the first message to be from the user; our
    # interview transcripts can start with the interviewer (assistant).
    if not chat or chat[0]["role"] != "user":
        chat.insert(0, {"role": "user", "content": "[The session begins.]"})

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=settings.resolved_model,
                max_tokens=16000,
                system=system,
                messages=chat,
            )
        except anthropic.AnthropicError as exc:
            raise _friendly_provider_error(exc, "anthropic") from exc
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
