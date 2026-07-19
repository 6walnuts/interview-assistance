"""Voice endpoints run against mock mode (conftest sets MOCK_AI=true)."""


def test_transcribe_returns_mock_text(client, auth_headers):
    resp = client.post(
        "/api/voice/transcribe",
        content=b"\x00" * 256,
        headers={**auth_headers, "Content-Type": "audio/webm"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["text"]


def test_transcribe_rejects_empty_upload(client, auth_headers):
    resp = client.post("/api/voice/transcribe", content=b"", headers=auth_headers)
    assert resp.status_code == 400


def test_tts_returns_playable_audio(client, auth_headers):
    resp = client.post("/api/voice/tts", json={"text": "Hello candidate"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/")
    assert resp.content[:4] == b"RIFF"  # mock mode emits a valid WAV


def test_tts_rejects_blank_text(client, auth_headers):
    resp = client.post("/api/voice/tts", json={"text": "   "}, headers=auth_headers)
    assert resp.status_code == 400


def test_voice_requires_auth(client):
    assert client.post("/api/voice/tts", json={"text": "hi"}).status_code == 401
