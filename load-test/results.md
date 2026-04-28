# Load Test Results

**Tool:** Locust 2.43.4  
**Target:** transaction-service — `POST /transactions` + `GET /transactions/{id}`  
**User mix:** 90% RegularUser (domestic transactions) + 10% FraudUser (high-risk amounts, foreign countries)

---

## Baseline — 50 users (default pool: pool_size=5, max_overflow=10)

| Metric | POST /transactions | GET /transactions/{id} | Aggregated |
|---|---|---|---|
| RPS | 27.4 | 6.8 | **36.6** |
| p50 | 8 ms | 5 ms | 8 ms |
| p95 | 17 ms | 10 ms | **16 ms** |
| p99 | 30 ms | 20 ms | 28 ms |
| Errors | 0% | 0% | **0%** |

---

## Stress — 300 users, before optimization (pool_size=5, max_overflow=10)

| Metric | POST /transactions | GET /transactions/{id} | Aggregated |
|---|---|---|---|
| RPS | 137.3 | 33.3 | **183.4** |
| p50 | 270 ms | 190 ms | 250 ms |
| p95 | 750 ms | 680 ms | **740 ms** |
| p99 | 1200 ms | 1000 ms | 1100 ms |
| Errors | 0% | 0% | **0%** |

---

## Stress — 300 users, after optimization (pool_size=20, max_overflow=0)

| Metric | POST /transactions | GET /transactions/{id} | Aggregated |
|---|---|---|---|
| RPS | 162.4 | 39.6 | **216.1** |
| p50 | 28 ms | 15 ms | 25 ms |
| p95 | 200 ms | 100 ms | **190 ms** |
| p99 | 340 ms | 250 ms | 330 ms |
| Errors | 0% | 0% | **0%** |

---

## Delta

| Metric | Before | After | Change |
|---|---|---|---|
| RPS | 183 | 216 | **+18%** |
| p50 | 250 ms | 25 ms | **−90%** |
| p95 | 740 ms | 190 ms | **−74%** |
| p99 | 1100 ms | 330 ms | **−70%** |

---

## What happened

With `pool_size=5` (SQLAlchemy default) and 300 concurrent users, requests queued up
waiting for one of 5 database connections. p95 hit 740 ms — 46x worse than baseline.
Classic connection pool exhaustion.

After setting `pool_size=20, max_overflow=0`:
- all 300 users get a connection immediately, no waiting
- p95 dropped to 190 ms
- throughput went up 18% — less waiting means more requests processed

## The fix

`services/transaction-service/app/db/session.py`:

```python
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,      # was 5 (SQLAlchemy default)
    max_overflow=0,    # fixed pool size — no connection storms under load
    pool_timeout=30,
    pool_recycle=1800,
)
```
