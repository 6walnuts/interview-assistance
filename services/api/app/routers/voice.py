"""Voice endpoints: speech-to-text, text-to-speech and realtime voice calls.

Audio uploads arrive as a raw request body (audio/webm etc.), not multipart.
In mock mode (MOCK_AI=true / no key) transcribe/tts return deterministic
output — a fixed transcript and a short silent WAV — so the whole loop stays
offline-runnable and testable. Realtime calls need a real OpenAI key: the
browser connects to OpenAI over WebRTC with a short-lived ephemeral secret
minted here, and both sides' transcripts are posted back so the Scoring
Agent sees the full conversation.
"""
import io
import wave

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..agents.llm import AgentError, _friendly_provider_error, _validated_api_key
from ..agents.prompts import language_instruction
from ..config import get_settings
from ..db import get_db
from ..models import InterviewMessage, User
from ..schemas import (
    MessageOut,
    RealtimeSessionOut,
    RealtimeSessionRequest,
    RealtimeToolIn,
    RealtimeToolOut,
    RealtimeTranscriptIn,
    TranscriptionOut,
    TTSRequest,
)
from ..security import get_current_user
from ..services.interview_service import _locale
from .interviews import _owned_session, _require_in_progress

router = APIRouter(prefix="/api/voice", tags=["voice"])

MOCK_TRANSCRIPT = "This is a mock transcription of your voice input."
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # OpenAI upload limit
MAX_TTS_CHARS = 4000

_EXT_BY_CONTENT_TYPE = {
    "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4",
    "audio/mpeg": "mp3", "audio/wav": "wav", "audio/x-wav": "wav",
}


def _openai_client():
    settings = get_settings()
    if settings.llm_provider != "openai":
        raise AgentError(
            "语音功能需要 OpenAI 的语音 API，目前只在 LLM_PROVIDER=openai 时可用。")
    from openai import OpenAI

    return OpenAI(api_key=_validated_api_key(settings), base_url=settings.resolved_base_url)


def _silent_wav(duration_s: float = 0.3, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * duration_s))
    return buf.getvalue()


@router.post("/transcribe", response_model=TranscriptionOut)
async def transcribe(
    request: Request, user: User = Depends(get_current_user)
) -> TranscriptionOut:
    settings = get_settings()
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio upload too large (max 25 MB)")
    if not settings.ai_enabled:
        return TranscriptionOut(text=MOCK_TRANSCRIPT)

    client = _openai_client()
    content_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    ext = _EXT_BY_CONTENT_TYPE.get(content_type, "webm")
    from openai import OpenAIError

    try:
        result = client.audio.transcriptions.create(
            model=settings.voice_stt_model, file=(f"speech.{ext}", audio),
        )
    except OpenAIError as exc:
        raise _friendly_provider_error(exc, "openai") from exc
    return TranscriptionOut(text=result.text)


@router.post("/tts")
def tts(body: TTSRequest, user: User = Depends(get_current_user)) -> Response:
    settings = get_settings()
    text = body.text.strip()[:MAX_TTS_CHARS]
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    if not settings.ai_enabled:
        return Response(content=_silent_wav(), media_type="audio/wav")

    client = _openai_client()
    from openai import OpenAIError

    try:
        speech = client.audio.speech.create(
            model=settings.voice_tts_model,
            voice=body.voice or settings.voice_tts_voice,
            input=text,
            response_format="mp3",
        )
    except OpenAIError as exc:
        raise _friendly_provider_error(exc, "openai") from exc
    return Response(content=speech.read(), media_type="audio/mpeg")


# ---------- realtime voice calls ----------

def _realtime_instructions(session, question, locale: str) -> str:
    from ..agents.interviewer import _format_question
    from ..agents.prompts import REALTIME_INTERVIEWER_SYSTEM

    return language_instruction(locale) + REALTIME_INTERVIEWER_SYSTEM.format(
        company_style=session.company_style,
        level=session.level,
        role=session.role,
        interview_type=session.interview_type,
        question=_format_question(question),
        current_stage=session.current_stage,
    )


def _realtime_tools() -> list[dict]:
    from ..agents.interviewer import STAGES

    return [
        {
            "type": "function",
            "name": "advance_stage",
            "description": "Move the interview to a new stage. Call this the moment "
                           "the conversation transitions, before speaking the first "
                           "line of the new stage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "enum": list(STAGES)},
                    "reason": {"type": "string",
                               "description": "One short sentence on why the stage advances now."},
                },
                "required": ["stage"],
            },
        },
        {
            "type": "function",
            "name": "record_observation",
            "description": "Log a private evaluation note about the candidate "
                           "(signal quality, strengths, mistakes, hint usage). "
                           "The candidate never sees these; the scoring agent does.",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
            },
        },
    ]


@router.post("/realtime-session", response_model=RealtimeSessionOut)
def realtime_session(
    body: RealtimeSessionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RealtimeSessionOut:
    session = _owned_session(body.interview_id, user, db)
    _require_in_progress(session)
    settings = get_settings()
    if not settings.ai_enabled:
        raise AgentError(
            "实时语音通话需要真实的 OpenAI key（MOCK_AI=false 且已配置 LLM_API_KEY）。"
            "🎙 录音转写和 🔊 朗读在 mock 模式下仍可用。")
    if settings.llm_provider != "openai":
        raise AgentError("实时语音通话需要 OpenAI 的 Realtime API，仅 LLM_PROVIDER=openai 可用。")

    key = _validated_api_key(settings)
    base_url = settings.resolved_base_url or "https://api.openai.com/v1"
    instructions = _realtime_instructions(session, session.question, _locale(db, user.id))
    try:
        resp = httpx.post(
            f"{base_url}/realtime/client_secrets",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "expires_after": {"anchor": "created_at", "seconds": 600},
                "session": {
                    "type": "realtime",
                    "model": settings.voice_realtime_model,
                    "instructions": instructions,
                    "tools": _realtime_tools(),
                    "tool_choice": "auto",
                    "audio": {
                        "input": {"transcription": {"model": settings.voice_stt_model}},
                        "output": {"voice": settings.voice_tts_voice},
                    },
                },
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise AgentError(f"无法连接 OpenAI Realtime API：{exc}") from exc
    if resp.status_code >= 400:
        raise _friendly_provider_error(RuntimeError(resp.text), "openai")
    data = resp.json()
    secret = data.get("value") or (data.get("client_secret") or {}).get("value", "")
    if not secret:
        raise AgentError(f"OpenAI Realtime API 返回了意外的响应格式：{str(data)[:200]}")
    return RealtimeSessionOut(
        client_secret=secret,
        model=settings.voice_realtime_model,
        expires_at=data.get("expires_at"),
    )


@router.post("/realtime-transcript", response_model=MessageOut)
def realtime_transcript(
    body: RealtimeTranscriptIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    """Persist one voice-call transcript line into interview_messages so the
    conversation shows in the chat history and the Scoring Agent grades it."""
    session = _owned_session(body.interview_id, user, db)
    _require_in_progress(session)
    msg = InterviewMessage(
        session_id=session.id, role=body.role, content=body.content.strip(),
        stage=session.current_stage,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(id=msg.id, role=msg.role, content=msg.content,
                      stage=msg.stage, created_at=msg.created_at)


@router.post("/realtime-tool", response_model=RealtimeToolOut)
def realtime_tool(
    body: RealtimeToolIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RealtimeToolOut:
    """Execute a function call made by the realtime voice interviewer.

    The browser relays the model's tool calls here; the result goes back over
    the data channel. Observations and stage-change reasons land in
    `internal_observation` on system messages — excluded from transcripts and
    API responses, but fed to the Scoring Agent like the text interviewer's notes.
    """
    from ..agents.interviewer import STAGES

    session = _owned_session(body.interview_id, user, db)
    _require_in_progress(session)

    if body.name == "advance_stage":
        stage = str(body.arguments.get("stage", ""))
        if stage not in STAGES:
            return RealtimeToolOut(
                result={"ok": False, "error": f"unknown stage '{stage}'"},
                current_stage=session.current_stage,
            )
        session.current_stage = stage
        db.add(InterviewMessage(
            session_id=session.id, role="system", content=f"[voice] stage -> {stage}",
            stage=stage,
            internal_observation={
                "candidate_signal": f"voice interviewer advanced to {stage}",
                "recommended_follow_up": str(body.arguments.get("reason", "")),
                "hint_level": 0,
            },
        ))
        db.commit()
        return RealtimeToolOut(result={"ok": True, "stage": stage}, current_stage=stage)

    if body.name == "record_observation":
        note = str(body.arguments.get("note", "")).strip()
        if not note:
            return RealtimeToolOut(result={"ok": False, "error": "empty note"},
                                   current_stage=session.current_stage)
        db.add(InterviewMessage(
            session_id=session.id, role="system", content="[voice] observation",
            stage=session.current_stage,
            internal_observation={"candidate_signal": note[:2000], "hint_level": 0},
        ))
        db.commit()
        return RealtimeToolOut(result={"ok": True}, current_stage=session.current_stage)

    return RealtimeToolOut(result={"ok": False, "error": f"unknown tool '{body.name}'"},
                           current_stage=session.current_stage)
