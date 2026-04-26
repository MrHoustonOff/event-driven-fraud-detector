import pytest
from httpx import AsyncClient


# Test 1: list rules when empty
async def test_list_rules_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/rules", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# Test 2: create rule success
async def test_create_rule(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/rules",
        json={"name": "LargeAmountRule", "weight": 30, "is_active": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "LargeAmountRule"
    assert data["weight"] == 30
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


# Test 3: duplicate rule name → 400
async def test_create_rule_duplicate_name(client: AsyncClient, auth_headers: dict, seeded_rule: dict):
    resp = await client.post(
        "/rules",
        json={"name": seeded_rule["name"], "weight": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# Test 4: filter by is_active
async def test_list_rules_filter_active(client: AsyncClient, auth_headers: dict, seeded_rule: dict):
    await client.put(
        f"/rules/{seeded_rule['id']}",
        json={"is_active": False},
        headers=auth_headers,
    )
    resp = await client.get("/rules?is_active=true", headers=auth_headers)
    assert resp.status_code == 200
    assert all(r["is_active"] for r in resp.json())


# Test 5: update rule
async def test_update_rule(client: AsyncClient, auth_headers: dict, seeded_rule: dict):
    resp = await client.put(
        f"/rules/{seeded_rule['id']}",
        json={"weight": 50},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["weight"] == 50
    assert resp.json()["name"] == seeded_rule["name"]


# Test 6: update non-existent rule → 404
async def test_update_rule_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/rules/9999", json={"weight": 50}, headers=auth_headers)
    assert resp.status_code == 404


# Test 7: delete rule → 204, then list → empty
async def test_delete_rule(client: AsyncClient, auth_headers: dict, seeded_rule: dict):
    resp = await client.delete(f"/rules/{seeded_rule['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/rules", headers=auth_headers)
    assert resp.json() == []


# Test 8: delete non-existent rule → 404
async def test_delete_rule_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/rules/9999", headers=auth_headers)
    assert resp.status_code == 404


# Test 9: any rules endpoint without token → 401
async def test_rules_unauthenticated(client: AsyncClient):
    assert (await client.get("/rules")).status_code == 401
    assert (await client.post("/rules", json={"name": "x", "weight": 10})).status_code == 401
