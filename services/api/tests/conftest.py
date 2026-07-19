import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["MOCK_AI"] = "true"
os.environ["SANDBOX_MODE"] = "subprocess"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post("/api/auth/register", json={
        "email": "candidate@example.com", "password": "secret123", "name": "Test Candidate",
    })
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
