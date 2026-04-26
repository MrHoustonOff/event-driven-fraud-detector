import pytest
from httpx import AsyncClient


# Test 1: register success
async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={"username": "newuser", "password": "password123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


# Test 2: duplicate username → 400
async def test_register_duplicate(client: AsyncClient):
    payload = {"username": "dupuser", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400


# Test 3: login success → JWT token
async def test_login_success(client: AsyncClient, registered_user: dict):
    resp = await client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"].startswith("eyJ")


# Test 4: wrong password → 401
async def test_login_wrong_password(client: AsyncClient, registered_user: dict):
    resp = await client.post("/auth/login", json={
        "username": registered_user["username"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


# Test 5: unknown user → 401
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/auth/login", json={"username": "ghost", "password": "password123"})
    assert resp.status_code == 401


# Test 6: GET /me with valid token → 200
async def test_get_me_with_token(client: AsyncClient, registered_user: dict, auth_headers: dict):
    resp = await client.get("/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == registered_user["username"]


# Test 7: GET /me without token → 401
async def test_get_me_without_token(client: AsyncClient):
    resp = await client.get("/me")
    assert resp.status_code == 401


# Test 8: GET /me with invalid token → 401
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get("/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
