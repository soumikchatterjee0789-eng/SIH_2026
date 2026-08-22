def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "password123", "full_name": "Alice", "user_type": "student"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]

    # duplicate registration must fail
    resp2 = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "password123", "full_name": "Alice", "user_type": "student"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["error_code"] == "ALREADY_EXISTS"

    # login (json variant)
    resp3 = client.post("/api/auth/login-json", json={"email": "alice@example.com", "password": "password123"})
    assert resp3.status_code == 200
    assert resp3.json()["data"]["access_token"]

    # wrong password
    resp4 = client.post("/api/auth/login-json", json={"email": "alice@example.com", "password": "wrong"})
    assert resp4.status_code == 401
    assert resp4.json()["error_code"] == "UNAUTHORIZED"


def test_protected_route_requires_token(client):
    resp = client.get("/api/users/me")
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "UNAUTHORIZED"


def test_get_me(auth_client):
    client, headers = auth_client
    resp = client.get("/api/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["email"].startswith("user_")
