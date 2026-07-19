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


def _create_interview(client, auth_headers) -> str:
    resp = client.post("/api/interviews", json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "company_style": "general", "duration_minutes": 45, "difficulty": "medium",
        "language": "python", "focus_areas": [],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["session"]["id"]


def test_realtime_session_needs_real_key(client, auth_headers):
    # Mock mode cannot mint an ephemeral OpenAI secret — expect a readable 502.
    session_id = _create_interview(client, auth_headers)
    resp = client.post("/api/voice/realtime-session",
                       json={"interview_id": session_id}, headers=auth_headers)
    assert resp.status_code == 502
    assert "OpenAI" in resp.json()["detail"]


def test_realtime_transcript_persists_to_interview(client, auth_headers):
    session_id = _create_interview(client, auth_headers)
    for role, content in [("candidate", "I would use a hash map here."),
                          ("interviewer", "Walk me through the complexity.")]:
        resp = client.post("/api/voice/realtime-transcript", json={
            "interview_id": session_id, "role": role, "content": content,
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["role"] == role and body["content"] == content
        assert "internal_observation" not in body

    detail = client.get(f"/api/interviews/{session_id}", headers=auth_headers).json()
    contents = [m["content"] for m in detail["messages"]]
    assert "I would use a hash map here." in contents
    assert "Walk me through the complexity." in contents

    # The voice transcript feeds the normal scoring flow.
    end = client.post(f"/api/interviews/{session_id}/end", headers=auth_headers)
    assert end.status_code == 200, end.text


def test_realtime_transcript_rejects_ended_interview(client, auth_headers):
    session_id = _create_interview(client, auth_headers)
    client.post(f"/api/interviews/{session_id}/end", headers=auth_headers)
    resp = client.post("/api/voice/realtime-transcript", json={
        "interview_id": session_id, "role": "candidate", "content": "late line",
    }, headers=auth_headers)
    assert resp.status_code == 409


def test_realtime_tool_advance_stage(client, auth_headers):
    session_id = _create_interview(client, auth_headers)
    resp = client.post("/api/voice/realtime-tool", json={
        "interview_id": session_id, "name": "advance_stage",
        "arguments": {"stage": "approach", "reason": "candidate finished clarifying"},
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["ok"] is True
    assert body["current_stage"] == "approach"

    detail = client.get(f"/api/interviews/{session_id}", headers=auth_headers)
    assert detail.json()["session"]["current_stage"] == "approach"


def test_realtime_tool_rejects_unknown_stage_and_tool(client, auth_headers):
    session_id = _create_interview(client, auth_headers)
    bad_stage = client.post("/api/voice/realtime-tool", json={
        "interview_id": session_id, "name": "advance_stage", "arguments": {"stage": "lunch"},
    }, headers=auth_headers).json()
    assert bad_stage["result"]["ok"] is False

    bad_tool = client.post("/api/voice/realtime-tool", json={
        "interview_id": session_id, "name": "give_score", "arguments": {},
    }, headers=auth_headers).json()
    assert bad_tool["result"]["ok"] is False


def test_realtime_observations_stay_private(client, auth_headers):
    """Voice observations must feed scoring but never appear in API responses."""
    session_id = _create_interview(client, auth_headers)
    secret_note = "PRIVATE-NOTE: candidate confused Kafka offsets with partitions"
    resp = client.post("/api/voice/realtime-tool", json={
        "interview_id": session_id, "name": "record_observation",
        "arguments": {"note": secret_note},
    }, headers=auth_headers)
    assert resp.json()["result"]["ok"] is True

    detail = client.get(f"/api/interviews/{session_id}", headers=auth_headers)
    raw = detail.text
    assert secret_note not in raw
    assert "internal_observation" not in raw
    assert all(m["role"] != "system" for m in detail.json()["messages"])

    # Ending still works with system notes present, and the report never leaks them.
    end = client.post(f"/api/interviews/{session_id}/end", headers=auth_headers)
    assert end.status_code == 200, end.text
    report = client.get(f"/api/interviews/{session_id}/report", headers=auth_headers)
    assert secret_note not in report.text
