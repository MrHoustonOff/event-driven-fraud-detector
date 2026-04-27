# Результаты нагрузочного теста

## Конфигурация
- Инструмент: Locust 2.43.4
- Сервис: transaction-service (POST /transactions + GET /transactions/{id})
- Профиль: 90% RegularUser (85% RU / 15% зарубежные) + 10% FraudUser (TH/AE/CN, суммы 30k–100k)
- Стресс-нагрузка: 300 concurrent users, ramp-up 30/s, 3 min
- Baseline: 50 concurrent users, ramp-up 5/s, 2 min

## Baseline — 50 users (pool_size=5, max_overflow=10)

| Метрика    | POST /transactions | GET /transactions/{id} | Aggregated |
|------------|-------------------|------------------------|------------|
| RPS        | 27.4              | 6.8                    | **36.6**   |
| p50        | 8 ms              | 5 ms                   | 8 ms       |
| p95        | 17 ms             | 10 ms                  | **16 ms**  |
| p99        | 30 ms             | 20 ms                  | 28 ms      |
| Error rate | 0%                | 0%                     | **0%**     |

## Стресс ДО оптимизации — 300 users (pool_size=5, max_overflow=10)

| Метрика    | POST /transactions | GET /transactions/{id} | Aggregated  |
|------------|-------------------|------------------------|-------------|
| RPS        | 137.3             | 33.3                   | **183.4**   |
| p50        | 270 ms            | 190 ms                 | 250 ms      |
| p95        | 750 ms            | 680 ms                 | **740 ms**  |
| p99        | 1200 ms           | 1000 ms                | 1100 ms     |
| Error rate | 0%                | 0%                     | **0%**      |

## Стресс ПОСЛЕ оптимизации — 300 users (pool_size=20, max_overflow=0)

| Метрика    | POST /transactions | GET /transactions/{id} | Aggregated  |
|------------|-------------------|------------------------|-------------|
| RPS        | 162.4             | 39.6                   | **216.1**   |
| p50        | 28 ms             | 15 ms                  | 25 ms       |
| p95        | 200 ms            | 100 ms                 | **190 ms**  |
| p99        | 340 ms            | 250 ms                 | 330 ms      |
| Error rate | 0%                | 0%                     | **0%**      |

## Δ (улучшение при переходе от default pool к оптимизированному, 300 users)

| Метрика | До    | После | Улучшение |
|---------|-------|-------|-----------|
| RPS     | 183   | 216   | **+18%**  |
| p50     | 250ms | 25ms  | **-90%**  |
| p95     | 740ms | 190ms | **-74%**  |
| p99     | 1100ms| 330ms | **-70%**  |

## Что произошло

При `pool_size=5` (SQLAlchemy default) и 300 concurrent users запросы выстраивались
в очередь к пулу из 5 соединений. Каждый запрос ждал свободного слота → p95 вырос до
740ms (в 46× хуже baseline). Это классическая **connection pool exhaustion**.

После увеличения `pool_size=20` + `max_overflow=0`:
- Каждый из 300 users получает соединение без ожидания
- p95 упал до 190ms — укладывается в стандартный SLO < 200ms
- Throughput вырос на 18% (меньше времени на ожидание = больше запросов обработано)

## Оптимизация (`services/transaction-service/app/db/session.py`)

```python
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,      # было 5 (default)
    max_overflow=0,    # фиксированный пул, нет connection storm
    pool_timeout=30,   # явный timeout вместо бесконечного ожидания
    pool_recycle=1800, # переоткрывать соединения каждые 30 мин
)
```

## Для анкеты T-Bank

> Нагрузочный тест transaction-service (Locust): **216 RPS, p95 190ms** при 300 concurrent users.  
> До оптимизации connection pool: p95 740ms (pool_size=5 default).  
> После (pool_size=20, max_overflow=0): p95 190ms — **улучшение на 74%**.
