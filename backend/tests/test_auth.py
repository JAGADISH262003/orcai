def _register(client, email="a@b.com", agency="Test Co", password="password123"):
    return client.post(
        "/api/v1/auth/register",
        json={"agency_name": agency, "name": "Alice", "email": email, "password": password},
    )


def test_register_login_flow(client):
    r = _register(client)
    assert r.status_code == 201
    data = r.json()
    assert data["user"]["role"] == "owner"
    assert data["agency"]["slug"]

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "password123"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_duplicate_email_rejected(client):
    r = _register(client, email="dup@b.com")
    assert r.status_code == 201
    r2 = _register(client, email="dup@b.com")
    assert r2.status_code == 409


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(client):
    r = _register(client, email="me@b.com")
    token = r.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "me@b.com"
