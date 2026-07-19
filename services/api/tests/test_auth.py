def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "secret123", "name": "Dup"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "login@example.com", "password": "secret123", "name": "L"})
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_profile_requires_auth(client):
    assert client.get("/api/profile").status_code == 401


def test_profile_update(client, auth_headers):
    resp = client.put("/api/profile", headers=auth_headers, json={
        "target_role": "Senior Backend Engineer", "target_level": "senior",
        "weekly_hours": 10, "onboarding_completed": True,
    })
    assert resp.status_code == 200
    body = resp.json()["profile"]
    assert body["target_role"] == "Senior Backend Engineer"
    assert body["onboarding_completed"] is True
