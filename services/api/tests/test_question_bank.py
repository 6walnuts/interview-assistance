"""Classic system-design question bank integrity."""
from app.seed import QUESTIONS
from app.seed_questions import CLASSIC_QUESTIONS


def test_bank_size_and_unique_titles():
    all_q = [*QUESTIONS, *CLASSIC_QUESTIONS]
    titles = [q["title"] for q in all_q]
    assert len(CLASSIC_QUESTIONS) == 44
    assert len(titles) == len(set(titles)), "duplicate question titles"


def test_classic_questions_are_well_formed():
    from app.seed import TOPICS

    valid_slugs = {t["slug"] for t in TOPICS}
    for q in CLASSIC_QUESTIONS:
        assert q["interview_type"] == "system_design", q["title"]
        assert q["difficulty"] in {"easy", "medium", "hard"}, q["title"]
        assert q["category"] in valid_slugs, f"{q['title']}: unknown category {q['category']}"
        assert len(q["prompt"]) > 100, q["title"]
        assert len(q["rubric"]["expected"]) >= 4, q["title"]


def test_seeded_bank_serves_system_design_interviews(client, auth_headers):
    # A system-design interview must come back with a question from the bank.
    resp = client.post("/api/interviews", json={
        "interview_type": "system_design", "role": "Backend Engineer", "level": "senior",
        "company_style": "general", "duration_minutes": 45, "difficulty": "hard",
        "language": "python", "focus_areas": ["payment-system", "idempotency"],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    q = resp.json()["question"]
    assert q["title"]
    assert q["prompt"]
