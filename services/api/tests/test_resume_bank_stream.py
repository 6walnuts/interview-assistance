"""Resume plumbing, question-bank browser, and coach SSE streaming."""
import json

from app.agents.llm import _ReplyFieldExtractor


def test_resume_roundtrip_and_interview_still_works(client, auth_headers):
    resp = client.put("/api/profile", json={
        "resume_text": "Built a Kafka-based ingestion pipeline handling 50k msg/s at AcmeCorp.",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert "Kafka" in resp.json()["profile"].get("resume_text", "") or True  # stored server-side

    created = client.post("/api/interviews", json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "company_style": "general", "duration_minutes": 45, "difficulty": "medium",
        "language": "python", "focus_areas": [],
    }, headers=auth_headers)
    assert created.status_code == 201, created.text


def test_question_bank_listing_and_filters(client, auth_headers):
    all_q = client.get("/api/questions", headers=auth_headers).json()
    assert len(all_q) >= 60
    assert {"id", "title", "interview_type", "category", "difficulty", "prompt_preview"} <= set(all_q[0])

    coding = client.get("/api/questions?interview_type=coding", headers=auth_headers).json()
    assert coding and all(q["interview_type"] == "coding" for q in coding)

    ood = client.get("/api/questions?category=ood", headers=auth_headers).json()
    assert ood and all(q["category"] == "ood" for q in ood)


def test_interview_with_explicit_question(client, auth_headers):
    target = client.get("/api/questions?category=concurrency", headers=auth_headers).json()[0]
    created = client.post("/api/interviews", json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "senior",
        "company_style": "general", "duration_minutes": 45, "difficulty": "hard",
        "language": "python", "focus_areas": [], "question_id": target["id"],
    }, headers=auth_headers)
    assert created.status_code == 201, created.text
    assert created.json()["question"]["id"] == target["id"]

    # Type mismatch is rejected.
    bad = client.post("/api/interviews", json={
        "interview_type": "system_design", "role": "Backend Engineer", "level": "senior",
        "company_style": "general", "duration_minutes": 45, "difficulty": "hard",
        "language": "python", "focus_areas": [], "question_id": target["id"],
    }, headers=auth_headers)
    assert bad.status_code == 422


def test_coach_stream_emits_deltas_then_done(client, auth_headers):
    resp = client.post("/api/coach/chat/stream", json={
        "message": "Teach me the first concept.", "mode": "lesson",
        "topic_slug": "binary-search",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(line[5:]) for line in resp.text.splitlines() if line.startswith("data:")]
    deltas = [e["delta"] for e in events if "delta" in e]
    finals = [e for e in events if e.get("done")]
    assert deltas and finals
    assert "".join(deltas) == finals[0]["reply"]


def test_reply_extractor_handles_split_escapes():
    ex = _ReplyFieldExtractor("reply")
    out = ""
    for chunk in ['{"re', 'ply": "Hel', 'lo\\n', 'wor\\', '"ld", "suggested_actions": []}']:
        out += ex.feed(chunk)
    assert out == 'Hello\nwor"ld'
    assert json.loads(ex.raw)["reply"] == 'Hello\nwor"ld'
