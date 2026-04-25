VALID_TX = {
    "user_id": 1,
    "amount": "1000.00",
    "currency": "RUB",
    "country": "RU",
    "city": "Moscow",
    "merchant": "Magnit",
}


async def test_create_transaction_returns_202(client):
    resp = await client.post("/transactions", json=VALID_TX)
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    assert data["amount"] == "1000.00"


async def test_get_transaction(client):
    create_resp = await client.post("/transactions", json=VALID_TX)
    tx_id = create_resp.json()["id"]

    get_resp = await client.get(f"/transactions/{tx_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == tx_id


async def test_get_transaction_not_found(client):
    resp = await client.get("/transactions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_create_transaction_invalid_amount(client):
    resp = await client.post("/transactions", json={**VALID_TX, "amount": "-100"})
    assert resp.status_code == 422


async def test_create_transaction_invalid_user_id(client):
    resp = await client.post("/transactions", json={**VALID_TX, "user_id": 0})
    assert resp.status_code == 422


async def test_create_transaction_invalid_country(client):
    resp = await client.post("/transactions", json={**VALID_TX, "country": "RUS"})
    assert resp.status_code == 422


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "connected"


async def test_kafka_publish_called_with_correct_args(client, publish_mock):
    await client.post("/transactions", json=VALID_TX)

    publish_mock.assert_called_once()
    topic, event = publish_mock.call_args[0]
    assert topic == "tx.raw"
    assert str(event.amount) == "1000.00"
    assert event.user_id == 1
    assert event.currency == "RUB"


async def test_kafka_down_still_returns_202(client, publish_mock):
    publish_mock.side_effect = Exception("Kafka unavailable")
    resp = await client.post("/transactions", json=VALID_TX)
    assert resp.status_code == 202
