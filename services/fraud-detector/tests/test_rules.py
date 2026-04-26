from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.rules import (
    FraudEngine,
    HighFrequencyRule,
    LargeAmountRule,
    NewCountryRule,
    NightTimeRule,
    TransactionContext,
    UnusualCityRule,
    VelocityAmountRule,
)
from shared.schemas import TransactionEvent


def make_tx(
    amount: float = 500,
    country: str = "RU",
    city: str = "Moscow",
    created_at: datetime | None = None,
) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=uuid4(),
        user_id=1,
        amount=Decimal(str(amount)),
        currency="RUB",
        country=country,
        city=city,
        merchant="Test",
        created_at=created_at or datetime.now(timezone.utc),
    )


# --- LargeAmountRule ---

async def test_large_amount_triggers_30():
    ctx = TransactionContext(tx=make_tx(35_000), history=[])
    assert await LargeAmountRule().score(ctx) == 30


async def test_large_amount_triggers_10():
    ctx = TransactionContext(tx=make_tx(15_000), history=[])
    assert await LargeAmountRule().score(ctx) == 10


async def test_large_amount_no_trigger():
    ctx = TransactionContext(tx=make_tx(500), history=[])
    assert await LargeAmountRule().score(ctx) == 0


# --- NewCountryRule ---

async def test_new_country_triggers():
    ctx = TransactionContext(
        tx=make_tx(country="TH"),
        history=[make_tx(country="RU")],
    )
    assert await NewCountryRule().score(ctx) == 40


async def test_new_country_no_trigger():
    ctx = TransactionContext(
        tx=make_tx(country="RU"),
        history=[make_tx(country="RU")],
    )
    assert await NewCountryRule().score(ctx) == 0


async def test_new_country_no_history():
    ctx = TransactionContext(tx=make_tx(country="TH"), history=[])
    assert await NewCountryRule().score(ctx) == 0


# --- HighFrequencyRule ---

async def test_high_frequency_triggers():
    now = datetime.now(timezone.utc)
    history = [make_tx(created_at=now - timedelta(minutes=i)) for i in range(1, 7)]
    ctx = TransactionContext(tx=make_tx(created_at=now), history=history)
    assert await HighFrequencyRule().score(ctx) == 25


async def test_high_frequency_no_trigger():
    now = datetime.now(timezone.utc)
    history = [make_tx(created_at=now - timedelta(minutes=i)) for i in range(1, 4)]
    ctx = TransactionContext(tx=make_tx(created_at=now), history=history)
    assert await HighFrequencyRule().score(ctx) == 0


# --- NightTimeRule ---

async def test_night_time_triggers():
    night = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)
    ctx = TransactionContext(tx=make_tx(created_at=night), history=[])
    assert await NightTimeRule().score(ctx) == 15


async def test_night_time_no_trigger():
    day = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    ctx = TransactionContext(tx=make_tx(created_at=day), history=[])
    assert await NightTimeRule().score(ctx) == 0


# --- UnusualCityRule ---

async def test_unusual_city_triggers():
    ctx = TransactionContext(
        tx=make_tx(city="Bangkok"),
        history=[make_tx(city="Moscow")],
    )
    assert await UnusualCityRule().score(ctx) == 20


async def test_unusual_city_no_trigger():
    ctx = TransactionContext(
        tx=make_tx(city="Moscow"),
        history=[make_tx(city="Moscow")],
    )
    assert await UnusualCityRule().score(ctx) == 0


# --- VelocityAmountRule ---

async def test_velocity_triggers():
    history = [make_tx(amount=1_000) for _ in range(5)]  # avg = 1000
    ctx = TransactionContext(tx=make_tx(amount=30_000), history=history)
    assert await VelocityAmountRule().score(ctx) == 20


async def test_velocity_no_trigger():
    history = [make_tx(amount=1_000)]  # avg = 1000
    ctx = TransactionContext(tx=make_tx(amount=500), history=history)
    assert await VelocityAmountRule().score(ctx) == 0


# --- FraudEngine ---

async def test_engine_thailand_blocked():
    night = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)
    tx = make_tx(amount=52_000, country="TH", city="Bangkok", created_at=night)
    history = [make_tx(amount=500, country="RU", city="Moscow")]

    engine = FraudEngine([
        LargeAmountRule(),
        NewCountryRule(),
        HighFrequencyRule(),
        NightTimeRule(),
        UnusualCityRule(),
        VelocityAmountRule(),
    ])
    score, triggered = await engine.evaluate(TransactionContext(tx=tx, history=history))

    assert score >= 70
    assert "LargeAmountRule" in triggered
    assert "NewCountryRule" in triggered
    assert "NightTimeRule" in triggered


async def test_engine_clean_transaction():
    day = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    tx = make_tx(amount=500, country="RU", city="Moscow", created_at=day)

    engine = FraudEngine([
        LargeAmountRule(),
        NewCountryRule(),
        HighFrequencyRule(),
        NightTimeRule(),
        UnusualCityRule(),
        VelocityAmountRule(),
    ])
    score, triggered = await engine.evaluate(TransactionContext(tx=tx, history=[]))

    assert score == 0
    assert triggered == []
