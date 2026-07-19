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
