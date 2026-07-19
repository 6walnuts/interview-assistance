"""Voice endpoints: speech-to-text and text-to-speech via OpenAI audio APIs.

Audio uploads arrive as a raw request body (audio/webm etc.), not multipart.
In mock mode (MOCK_AI=true / no key) both endpoints return deterministic
output — a fixed transcript and a short silent WAV — so the whole loop stays
offline-runnable and testable.
"""
import io
import wave

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..agents.llm import AgentError, _friendly_provider_error, _validated_api_key
from ..config import get_settings
from ..models import User
from ..schemas import TranscriptionOut, TTSRequest
from ..security import get_current_user

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
