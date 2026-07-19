"""Single-user local mode: no auth required, requests act as the local account."""
import pytest

from app.config import get_settings


@pytest.fixture()
def local_mode():
    settings = get_settings()
    settings.local_mode = True
    yield
    settings.local_mode = False


def test_no_auth_rejected_when_local_mode_off(client):
    assert client.get("/api/profile").status_code == 401


def test_local_mode_works_without_any_auth(client, local_mode):
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "local@localhost"

    # full flow works unauthenticated and persists to the same local account
    created = client.post("/api/interviews", json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "difficulty": "easy", "focus_areas": [],
    })
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    assert client.post(f"/api/interviews/{session_id}/end").status_code == 200
    tasks = client.get("/api/tasks").json()
    assert len(tasks) >= 3


def test_local_mode_ignores_invalid_token(client, local_mode):
    resp = client.get("/api/profile", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "local@localhost"
