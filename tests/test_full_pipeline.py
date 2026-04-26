import asyncio
import random

import httpx

TX_URL = "http://localhost:8000"
ADMIN_URL = "http://localhost:8004"

# Уникальные данные на каждый запуск — изолируем от предыдущих тестовых данных в БД
_RUN_ID = random.randint(100_000, 9_000_000)
USER_NORMAL = _RUN_ID
USER_FRAUD  = _RUN_ID + 1
USER_LIMIT  = _RUN_ID + 2


def _tx(user_id: int, amount: str, country: str = "RU", city: str = "Moscow") -> dict:
    return {
        "user_id": user_id,
        "amount": amount,
        "currency": "RUB",
        "country": country,
        "city": city,
        "merchant": "TestMerchant",
    }


async def _get_status(client: httpx.AsyncClient, tx_id: str) -> str:
    resp = await client.get(f"{TX_URL}/transactions/{tx_id}")
    return resp.json()["status"]


# Тест 1: 10 нормальных транзакций (RU, 500₽) → ни одна не BLOCKED
# score: tx1 = NewCountry(40) → APPROVED; tx7-10 = HighFreq(25) → APPROVED
async def test_normal_transactions_not_blocked():
    async with httpx.AsyncClient(timeout=30) as client:
        ids = []
        for _ in range(10):
            resp = await client.post(f"{TX_URL}/transactions", json=_tx(USER_NORMAL, "500.00"))
            assert resp.status_code == 202
            ids.append(resp.json()["transaction_id"])

        await asyncio.sleep(5)

        for tx_id in ids:
            status = await _get_status(client, tx_id)
            assert status != "BLOCKED", f"tx {tx_id} неожиданно BLOCKED"


# Тест 2: Таиланд + 52000₽ → NewCountry(40) + LargeAmount(30) = 70 → BLOCKED
async def test_fraud_transaction_blocked():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{TX_URL}/transactions",
            json=_tx(USER_FRAUD, "52000.00", country="TH", city="Bangkok"),
        )
        assert resp.status_code == 202
        tx_id = resp.json()["transaction_id"]

        await asyncio.sleep(5)

        assert await _get_status(client, tx_id) == "BLOCKED"


# Тест 3: превышение лимита → limits-service BLOCKED
# Устанавливаем daily_limit=1000₽ через admin-api, отправляем 2000₽
# fraud score = 40 (NewCountry, RU, < 10k) → fraud-detector не блокирует
# limits-service: 2000 > 1000 → BLOCKED
async def test_limit_exceeded_blocks_transaction():
    admin_name = f"e2e_{_RUN_ID}"

    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            f"{ADMIN_URL}/auth/register",
            json={"username": admin_name, "password": "testpass123"},
        )
        login = await client.post(
            f"{ADMIN_URL}/auth/login",
            json={"username": admin_name, "password": "testpass123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        await client.put(
            f"{ADMIN_URL}/users/{USER_LIMIT}/limits",
            json={"daily_limit": 1000, "monthly_limit": 5000},
            headers=headers,
        )

        resp = await client.post(f"{TX_URL}/transactions", json=_tx(USER_LIMIT, "2000.00"))
        assert resp.status_code == 202
        tx_id = resp.json()["transaction_id"]

        await asyncio.sleep(5)

        assert await _get_status(client, tx_id) == "BLOCKED"
