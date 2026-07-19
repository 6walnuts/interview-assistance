"""Chapter quizzes and the study-plan generator (mock AI mode)."""


def test_quiz_generation_hides_answers(client, auth_headers):
    resp = client.get("/api/quiz/arrays?count=4", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic_slug"] == "arrays"
    assert len(body["questions"]) == 4
    for q in body["questions"]:
        assert "answer_index" not in q and "explanation" not in q
        assert len(q["options"]) == 4

    # question bank persists: second fetch returns the same stored questions
    again = client.get("/api/quiz/arrays?count=4", headers=auth_headers).json()
    assert {q["id"] for q in again["questions"]} == {q["id"] for q in body["questions"]}


def test_quiz_submit_grades_and_updates_mastery(client, auth_headers):
    quiz = client.get("/api/quiz/two-pointers?count=4", headers=auth_headers).json()
    # mock generator always uses answer_index=0: answer 3 right, 1 wrong
    answers = [{"question_id": q["id"], "selected_index": 0} for q in quiz["questions"][:3]]
    answers.append({"question_id": quiz["questions"][3]["id"], "selected_index": 1})

    resp = client.post("/api/quiz/two-pointers/submit", headers=auth_headers,
                       json={"answers": answers})
    assert resp.status_code == 200
    body = resp.json()
    assert body["correct"] == 3 and body["total"] == 4
    assert body["mastery_score"] == 3 * 4 - 2  # +4 per correct, -2 per wrong
    wrong = [r for r in body["results"] if not r["is_correct"]]
    assert len(wrong) == 1 and wrong[0]["explanation"]

    skills = client.get("/api/progress/skills", headers=auth_headers).json()
    entry = next(s for s in skills if s["topic_slug"] == "two-pointers")
    assert entry["mastery_score"] == body["mastery_score"]


def test_quiz_rejects_foreign_question(client, auth_headers):
    other = client.get("/api/quiz/arrays?count=1", headers=auth_headers).json()
    resp = client.post("/api/quiz/two-pointers/submit", headers=auth_headers,
                       json={"answers": [{"question_id": other["questions"][0]["id"],
                                          "selected_index": 0}]})
    assert resp.status_code == 422


def test_unknown_topic_404(client, auth_headers):
    assert client.get("/api/quiz/not-a-topic", headers=auth_headers).status_code == 404


def test_study_plan_generation_and_regeneration(client, auth_headers):
    client.put("/api/profile", headers=auth_headers, json={
        "target_role": "Backend Engineer", "current_level": "mid", "target_level": "senior",
        "weekly_hours": 8, "weaknesses": ["caching", "sharding"], "onboarding_completed": True,
    })
    resp = client.post("/api/plan/generate", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["weeks"] >= 1 and body["task_count"] >= 3
    assert body["summary"]
    assert all(t["due_at"] for t in body["tasks"])
    assert any(t["task_type"] == "mock_interview" for t in body["tasks"])
    weeks = {t["week"] for t in body["tasks"]}
    assert min(weeks) == 1

    fetched = client.get("/api/plan", headers=auth_headers).json()
    assert fetched["task_count"] == body["task_count"]

    # regeneration replaces pending plan tasks instead of stacking duplicates
    again = client.post("/api/plan/generate", headers=auth_headers).json()
    final = client.get("/api/plan", headers=auth_headers).json()
    assert final["task_count"] == again["task_count"]


def test_passing_quiz_completes_matching_plan_task(client, auth_headers):
    plan = client.get("/api/plan", headers=auth_headers).json()
    quiz_tasks = [t for t in plan["tasks"] if t["task_type"] == "quiz" and t["topic_slug"]]
    assert quiz_tasks, "mock plan should contain quiz tasks"
    slug = quiz_tasks[0]["topic_slug"]

    quiz = client.get(f"/api/quiz/{slug}?count=5", headers=auth_headers).json()
    answers = [{"question_id": q["id"], "selected_index": 0} for q in quiz["questions"]]
    resp = client.post(f"/api/quiz/{slug}/submit", headers=auth_headers,
                       json={"answers": answers}).json()
    # mock questions are all answer_index=0 -> full score -> task auto-completed
    assert resp["correct"] == resp["total"]
    assert quiz_tasks[0]["id"] in resp["completed_task_ids"]
