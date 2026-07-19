"""End-to-end loop: create interview -> converse -> run code -> end -> report -> tasks."""

TWO_SUM = """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
    return []
"""


def _create_session(client, auth_headers):
    resp = client.post("/api/interviews", headers=auth_headers, json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "difficulty": "easy", "focus_areas": ["hash-map"],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_full_coding_interview_loop(client, auth_headers):
    created = _create_session(client, auth_headers)
    session_id = created["session"]["id"]
    assert created["question"]["title"]
    assert created["opening_message"]["role"] == "interviewer"
    assert "internal_observation" not in created["opening_message"]

    # converse: interviewer replies each turn and stage advances
    resp = client.post(f"/api/interviews/{session_id}/messages", headers=auth_headers,
                       json={"content": "Can I assume the array fits in memory?"})
    assert resp.status_code == 200
    assert resp.json()["message"]["role"] == "interviewer"

    # hint increments hint counter, does not crash
    resp = client.post(f"/api/interviews/{session_id}/messages", headers=auth_headers,
                       json={"content": "I'm stuck.", "action": "request_hint"})
    assert resp.status_code == 200

    # run code against seeded test cases
    resp = client.post(f"/api/interviews/{session_id}/run-code", headers=auth_headers,
                       json={"code": TWO_SUM, "label": "submit"})
    assert resp.status_code == 200
    execution = resp.json()["execution"]
    assert execution["exit_code"] == 0, execution["stderr"]
    assert execution["test_results"], "harness should produce test results"
    assert all(t["passed"] for t in execution["test_results"])

    # end -> report + auto-generated learning tasks (the core loop)
    resp = client.post(f"/api/interviews/{session_id}/end", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["review_task_count"] >= 3

    report = client.get(f"/api/interviews/{session_id}/report", headers=auth_headers).json()
    assert 1 <= report["overall_score"] <= 5
    assert report["hire_signal"] in {
        "strong_no_hire", "no_hire", "lean_no_hire", "mixed", "lean_hire", "hire", "strong_hire"}
    assert report["scores"]

    tasks = client.get("/api/tasks", headers=auth_headers).json()
    from_report = [t for t in tasks if t["source"] == "interview_report"]
    assert len(from_report) >= 3
    assert any(t["task_type"] == "mock_interview" for t in from_report)

    # ending again is idempotent
    assert client.post(f"/api/interviews/{session_id}/end", headers=auth_headers).status_code == 200

    # messaging a finished interview is rejected
    resp = client.post(f"/api/interviews/{session_id}/messages", headers=auth_headers,
                       json={"content": "hello?"})
    assert resp.status_code == 409


def test_run_code_failure_reported(client, auth_headers):
    created = _create_session(client, auth_headers)
    session_id = created["session"]["id"]
    resp = client.post(f"/api/interviews/{session_id}/run-code", headers=auth_headers,
                       json={"code": "def two_sum(nums, target):\n    return []", "label": "run"})
    assert resp.status_code == 200
    assert not all(t["passed"] for t in resp.json()["execution"]["test_results"])


def test_other_users_interview_is_forbidden(client, auth_headers):
    created = _create_session(client, auth_headers)
    other = client.post("/api/auth/register", json={
        "email": "intruder@example.com", "password": "secret123", "name": "I"}).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    resp = client.get(f"/api/interviews/{created['session']['id']}", headers=headers)
    assert resp.status_code == 403


def test_complete_task_updates_mastery(client, auth_headers):
    tasks = client.get("/api/tasks?status_filter=pending", headers=auth_headers).json()
    task = next(t for t in tasks if t["topic_slug"])
    resp = client.post(f"/api/tasks/{task['id']}/complete", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    # completing twice conflicts
    assert client.post(f"/api/tasks/{task['id']}/complete", headers=auth_headers).status_code == 409

    skills = client.get("/api/progress/skills", headers=auth_headers).json()
    assert any(s["topic_slug"] == task["topic_slug"] and s["mastery_score"] > 0 for s in skills)


def test_progress_overview(client, auth_headers):
    resp = client.get("/api/progress", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["interviews_completed"] >= 1
    assert body["tasks_completed"] >= 1
