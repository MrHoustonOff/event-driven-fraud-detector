import pytest
from httpx import AsyncClient


# Test 1: get limits for unknown user → 404
async def test_get_limits_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/users/9999/limits", headers=auth_headers)
    assert resp.status_code == 404


# Test 2: create limits via PUT (upsert)
async def test_create_limits_via_put(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/users/1/limits",
        json={"daily_limit": 200000, "monthly_limit": 1000000},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert float(data["daily_limit"]) == 200000
    assert float(data["monthly_limit"]) == 1000000


# Test 3: get limits after upsert
async def test_get_limits(client: AsyncClient, auth_headers: dict):
    await client.put(
        "/users/2/limits",
        json={"daily_limit": 50000, "monthly_limit": 300000},
        headers=auth_headers,
    )
    resp = await client.get("/users/2/limits", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["daily_limit"]) == 50000
    assert float(data["monthly_limit"]) == 300000


# Test 4: partial update — only daily_limit changes
async def test_update_partial_limits(client: AsyncClient, auth_headers: dict):
    await client.put(
        "/users/3/limits",
        json={"daily_limit": 100000, "monthly_limit": 500000},
        headers=auth_headers,
    )
    resp = await client.put(
        "/users/3/limits",
        json={"daily_limit": 150000},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["daily_limit"]) == 150000
    assert float(data["monthly_limit"]) == 500000


# Test 5: without token → 401
async def test_limits_unauthenticated(client: AsyncClient):
    assert (await client.get("/users/1/limits")).status_code == 401
    assert (await client.put("/users/1/limits", json={"daily_limit": 100000})).status_code == 401
