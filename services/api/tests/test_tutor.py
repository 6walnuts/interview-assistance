"""Tutor lesson mode, multi-turn coach history, and scratchpad code runs."""


def test_coach_lesson_mode_with_history(client, auth_headers):
    resp = client.post("/api/coach/chat", json={
        "message": "O(n log n), because the loop halves the range each time?",
        "mode": "lesson", "topic_slug": "binary-search",
        "history": [
            {"role": "user", "content": "Start the lesson."},
            {"role": "assistant", "content": "Lesson roadmap: ... What's the complexity?"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"]
    assert isinstance(body["suggested_actions"], list)


def test_lesson_anchored_on_question(client, auth_headers):
    q = client.get("/api/questions?category=caching", headers=auth_headers).json()[0]
    resp = client.post("/api/coach/chat", json={
        "message": f"Start the lesson focused on \"{q['title']}\".",
        "mode": "lesson", "topic_slug": "caching", "question_id": q["id"],
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["reply"]

    # Unknown question ids are ignored rather than erroring.
    ok = client.post("/api/coach/chat", json={
        "message": "hi", "mode": "lesson", "question_id": "nonexistent-id",
    }, headers=auth_headers)
    assert ok.status_code == 200


def test_coach_history_capped(client, auth_headers):
    too_long = [{"role": "user", "content": f"turn {i}"} for i in range(31)]
    resp = client.post("/api/coach/chat", json={
        "message": "hi", "mode": "lesson", "history": too_long,
    }, headers=auth_headers)
    assert resp.status_code == 422


def test_scratch_run_python(client, auth_headers):
    resp = client.post("/api/code/run", json={
        "code": "print(sum(range(5)))", "language": "python",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["exit_code"] == 0
    assert "10" in body["stdout"]


def test_scratch_run_requires_auth(client):
    assert client.post("/api/code/run", json={"code": "print(1)"}).status_code == 401


def test_interview_hint_returns_hint_content(client, auth_headers):
    resp = client.post("/api/interviews", json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "company_style": "general", "duration_minutes": 45, "difficulty": "medium",
        "language": "python", "focus_areas": [],
    }, headers=auth_headers)
    session_id = resp.json()["session"]["id"]

    normal = client.post(f"/api/interviews/{session_id}/messages", json={
        "content": "I'll start with a brute force.", "action": "message",
    }, headers=auth_headers).json()
    assert normal["hint_content"] == ""

    hint = client.post(f"/api/interviews/{session_id}/messages", json={
        "content": "Could I get a hint?", "action": "request_hint",
    }, headers=auth_headers).json()
    assert "TODO" in hint["hint_content"]

    # With editor contents attached, the hint builds on the candidate's code.
    my_code = "def two_sum(nums, target):\n    seen = {}\n"
    based = client.post(f"/api/interviews/{session_id}/messages", json={
        "content": "Could I get a hint?", "action": "request_hint",
        "current_code": my_code,
    }, headers=auth_headers).json()
    assert "seen = {}" in based["hint_content"]
    assert "TODO" in based["hint_content"]


def test_code_fences_hoisted_from_reply():
    from app.agents.agent_schemas import CoachReply
    from app.agents.coach import _hoist_code

    # Model put code in the chat text instead of code_snippet.
    r = _hoist_code(CoachReply(
        reply="Here is a frame:\n```python\ndef rag(q):\n    info = retrieve(q)\n    return generate(info)\n```\nContinue from it.",
        suggested_actions=[],
    ))
    assert r.code_snippet.startswith("def rag(q):")
    assert "```" not in r.reply
    assert "def rag" not in r.reply  # hoisted block removed from prose

    # Snippet already present: reply fences are just unfenced, snippet kept.
    r2 = _hoist_code(CoachReply(
        reply="Note ```x = 1``` inline.", suggested_actions=[], code_snippet="y = 2\n",
    ))
    assert r2.code_snippet == "y = 2\n"
    assert "```" not in r2.reply and "x = 1" in r2.reply

    # No fences: untouched.
    r3 = _hoist_code(CoachReply(reply="Plain text.", suggested_actions=[]))
    assert r3.reply == "Plain text." and r3.code_snippet == ""


def test_coach_hint_returns_code_snippet(client, auth_headers):
    resp = client.post("/api/coach/chat", json={
        "message": "I'm stuck — give me a hint for this exercise.",
        "mode": "lesson", "topic_slug": "binary-search",
    }, headers=auth_headers).json()
    assert "TODO" in resp["code_snippet"]

    plain = client.post("/api/coach/chat", json={
        "message": "explain the concept", "mode": "lesson", "topic_slug": "binary-search",
    }, headers=auth_headers).json()
    assert plain["code_snippet"] == ""


def test_lesson_realtime_session_needs_real_key(client, auth_headers):
    resp = client.post("/api/voice/realtime-session",
                       json={"topic_slug": "binary-search"}, headers=auth_headers)
    assert resp.status_code == 502
    assert "OpenAI" in resp.json()["detail"]


def test_realtime_session_requires_exactly_one_target(client, auth_headers):
    assert client.post("/api/voice/realtime-session", json={}, headers=auth_headers).status_code == 422
    assert client.post("/api/voice/realtime-session", json={
        "interview_id": "x", "topic_slug": "y",
    }, headers=auth_headers).status_code == 422
