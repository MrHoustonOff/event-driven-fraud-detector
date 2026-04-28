# Event-Driven Fraud Detector

Available in English: [README_en](docs/README_en.md)

Система обнаружения мошеннических транзакций в реальном времени.
Пять микросервисов на FastAPI, общение через Apache Kafka — без HTTP-вызовов между сервисами.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-KRaft-231F20?style=flat-square&logo=apache-kafka&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-83%2B_passed-4CAF50?style=flat-square&logo=pytest&logoColor=white)

---

## Как это работает

Клиент отправляет транзакцию — `transaction-service` валидирует, записывает в БД
со статусом `PENDING` и публикует событие в Kafka. Три консьюмера обрабатывают его
параллельно и независимо:

```
POST /transactions
  └─▶ transaction-service ──publish──▶ tx.raw
                                           ├─▶ fraud-detector   (7 правил → score 0–100)
                                           │       └─publish──▶ alerts ──▶ notify-service
                                           └─▶ limits-service   (дневной / месячный лимит)
                                                   └─publish──▶ limit_exceeded ──▶ notify-service
```

Клиент получил `202 Accepted` — транзакция уже в обработке. Через ~300 мс статус
изменится на `APPROVED`, `FLAGGED` или `BLOCKED`.

![Архитектура](docs/images/C4.png)

---

## Сервисы

| Сервис | Порт | Назначение |
|---|---|---|
| transaction-service | 8000 | Входная точка. Валидация, INSERT PENDING, publish в Kafka |
| fraud-detector | 8001 | 7 правил фрода → score 0–100 → обновление статуса в БД |
| limits-service | 8002 | Дневные и месячные лимиты трат пользователя |
| notify-service | 8003 | Webhook-уведомления об алертах и превышениях лимитов |
| admin-api | 8004 | CRUD правил и лимитов, JWT-аутентификация |

---

## Стек

| Слой | Технологии |
|---|---|
| API | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 async |
| Очередь | Apache Kafka 7.7 (KRaft), aiokafka |
| БД | PostgreSQL 16, asyncpg |
| Мониторинг | Prometheus, Grafana, structlog (JSON-логи) |
| Тесты | pytest, pytest-asyncio, httpx AsyncClient |
| Инфраструктура | Docker Compose, UV, Makefile |

---

## Запуск

**Требования:** Docker Desktop, Make (необязателен, можно использовать полные Docker команды).

```bash
git clone https://github.com/MrHoustonOff/event-driven-fraud-detector.git
cd event-driven-fraud-detector
cp .env.example .env
make up
```

Убедитесь, что все 10 контейнеров healthy:

```bash
make ps
```

```
NAME                    STATUS
transaction-service     healthy
fraud-detector          healthy
limits-service          healthy
notify-service          healthy
admin-api               healthy
postgres                healthy
kafka                   healthy
kafka-ui                healthy
prometheus              healthy
grafana                 healthy
```

| Адрес | Что |
|---|---|
| http://localhost:8000/docs | transaction-service — Swagger UI |
| http://localhost:8004/docs | admin-api — Swagger UI |
| http://localhost:8080 | Kafka UI — топики и сообщения |
| http://localhost:9090 | Prometheus |
| http://localhost:3000 | Grafana |

---

## API

### Создать транзакцию

`POST /transactions` принимает JSON:

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| user_id | integer | да | ID клиента (> 0) |
| amount | string (decimal) | да | Сумма, напр. `"1500.00"` |
| currency | string | нет | **ISO 4217**, DEFAULT `"RUB"` |
| country | string | да | **ISO 3166-1 alpha-2**, напр. `"RU"` |
| city | string | да | Город транзакции |
| merchant | string | да | Название магазина / сервиса |

Пример:

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount": "1500.00",
    "currency": "RUB",
    "country": "RU",
    "city": "Moscow",
    "merchant": "Wildberries"
  }'
# HTTP 202
# {"id": "550e8400-...", "status": "PENDING"}
```

### Посмотреть статус транзакции

```bash
curl http://localhost:8000/transactions/{id}
# {"id": "...", "status": "APPROVED", "fraud_score": 0, ...}
```

### admin-api

Аутентификация — JWT (Bearer token). Аналитики и риск-менеджеры логинятся по
`username` + `password`, получают токен и используют защищённые endpoints.

```bash
# Получить токен
curl -X POST http://localhost:8004/auth/login \
  -d "username=admin&password=secret"
# {"access_token": "eyJ...", "token_type": "bearer"}

# Использовать токен
curl http://localhost:8004/rules \
  -H "Authorization: Bearer eyJ..."
```

---

## Правила фрода

Движок построен на паттерне **Strategy**: каждое правило — отдельный класс с методом
`score()`. Баллы суммируются, кэп 100.

| Правило | Условие | Баллы |
|---|---|---|
| `LargeAmountRule` | сумма > 10 000 ₽ | +10 |
| `LargeAmountRule` | сумма > 30 000 ₽ | +30 (заменяет +10) |
| `NewCountryRule` | страна не встречалась в истории пользователя | +40 |
| `HighFrequencyRule` | >5 транзакций за последние 60 минут | +25 |
| `NightTimeRule` | время 02:00–05:00 UTC | +15 |
| `UnusualCityRule` | город не встречался в последних 30 транзакциях | +20 |
| `VelocityAmountRule` | сумма > средняя сумма пользователя × 3 | +20 |

| Score | Статус | Что происходит |
|---|---|---|
| < 50 | `APPROVED` | Транзакция проходит |
| 50–69 | `FLAGGED` | Проходит, помечена для ручного ревью |
| ≥ 70 | `BLOCKED` | Заблокирована автоматически |

---

## Жизнь транзакции



| Статус | Условие | Вебхук |
|---|---|---|
| `APPROVED` | score < 50, лимит в норме | нет |
| `FLAGGED` | score 50–69, лимит в норме | `fraud_alert` |
| `BLOCKED` | score ≥ 70 | `fraud_alert` |
| `BLOCKED` | лимит превышен | `limit_exceeded` |

`FLAGGED` — транзакция **одобрена и проведена**, но помечена для ручного ревью.
Аналитик видит её в дашборде и получает вебхук. Деньги при этом уже списаны.

![Transaction Lifecycle](docs/images/state.png)

---

## Схема базы данных

Один PostgreSQL, пять изолированных схем (упрощение для учебного проекта — в продакшне
каждый сервис имел бы собственную БД). Каждый сервис работает только со своей схемой.

### transactions.transactions

| Колонка | Тип | Ограничения |
|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| user_id | INTEGER | NOT NULL |
| amount | NUMERIC(15,2) | NOT NULL |
| currency | VARCHAR(3) | NOT NULL, DEFAULT 'RUB' |
| country | CHAR(2) | NOT NULL |
| city | VARCHAR(100) | NOT NULL |
| merchant | VARCHAR(255) | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' |
| fraud_score | INTEGER | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

| Индекс | Колонки | Зачем |
|---|---|---|
| idx_tx_user_created | (user_id, created_at DESC) | история пользователя для rule engine |
| idx_tx_status | (status) | выборка PENDING транзакций |

### fraud.rules

| Колонка | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| weight | INTEGER | NOT NULL, CHECK 0..100 |
| config_json | JSONB | nullable |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL |

### limits.user_limits

| Колонка | Тип | Ограничения |
|---|---|---|
| user_id | INTEGER | PK |
| daily_limit | NUMERIC(15,2) | NOT NULL, DEFAULT 100 000 |
| monthly_limit | NUMERIC(15,2) | NOT NULL, DEFAULT 500 000 |
| updated_at | TIMESTAMPTZ | NOT NULL |

### limits.spending_log

| Колонка | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| user_id | INTEGER | NOT NULL, FK → user_limits |
| amount | NUMERIC(15,2) | NOT NULL |
| transaction_id | UUID | NOT NULL, UNIQUE — idempotency |
| created_at | TIMESTAMPTZ | NOT NULL |

| Индекс | Колонки | Зачем |
|---|---|---|
| idx_spending_user_date | (user_id, created_at DESC) | агрегация трат за период |

### notify.notifications

| Колонка | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| user_id | INTEGER | NOT NULL |
| type | VARCHAR(50) | NOT NULL (`fraud_alert` / `limit_exceeded`) |
| payload | JSONB | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'sent' |
| error_message | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |

### auth.users

| Колонка | Тип | Ограничения |
|---|---|---|
| id | SERIAL | PK |
| username | VARCHAR(50) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(60) | NOT NULL — bcrypt, work_factor=12 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL |

---

## Нагрузочный тест

Locust, 300 concurrent users (90% RegularUser + 10% FraudUser), 3 минуты.

| Метрика | До оптимизации | После оптимизации | Δ |
|---|---|---|---|
| RPS | 183 | **216** | +18% |
| p50 | 250 ms | **25 ms** | −90% |
| p95 | 740 ms | **190 ms** | −74% |
| p99 | 1 100 ms | **330 ms** | −70% |
| Error rate | 0% | **0%** | — |

Узкое место — `pool_size=5` (SQLAlchemy default). При 300 users запросы вставали в
очередь к пяти соединениям. После `pool_size=20, max_overflow=0`: p95 упал с 740 до 190 мс.
Подробнее: [load-test/results/results.md](https://github.com/MrHoustonOff/event-driven-fraud-detector/blob/main/load-test/results/results.md).

---

## Тесты

```bash
# E2E тест — полный пайплайн: POST → Kafka → обновление статуса в БД
make test

# Тесты конкретного сервиса
cd services/fraud-detector && uv run pytest -v
cd services/transaction-service && uv run pytest -v
# ... аналогично для остальных
```

83+ тестов суммарно: юнит (каждое правило фрода в изоляции), интеграционные (роуты
через httpx AsyncClient), idempotency (UNIQUE constraint не пропускает дубли).

---

## Структура проекта

```
event-driven-fraud-detector/
├── shared/                   # Pydantic-схемы: TransactionEvent, AlertEvent, ...
├── services/
│   ├── transaction-service/  # FastAPI :8000
│   ├── fraud-detector/       # FastAPI :8001
│   ├── limits-service/       # FastAPI :8002
│   ├── notify-service/       # FastAPI :8003
│   └── admin-api/            # FastAPI :8004
├── postgres/init.sql         # DDL: схемы, таблицы, индексы
├── monitoring/               # prometheus.yml, Grafana dashboards
├── load-test/                # Locust сценарии + результаты
├── tests/                    # E2E тест полного пайплайна
├── docs/                     # C4 Container Diagram, ER Diagram
├── docker-compose.yml
└── Makefile
```

Каждый сервис следует одной структуре:

```
service-name/
├── app/
│   ├── main.py          # FastAPI app, lifespan (startup/shutdown)
│   ├── config.py        # pydantic-settings, переменные окружения
│   ├── models.py        # SQLAlchemy ORM модели
│   ├── schemas.py       # Pydantic схемы запросов и ответов
│   ├── db/session.py    # async engine, get_session dependency
│   ├── kafka/           # producer / consumer
│   └── routes/          # роуты FastAPI
├── tests/
├── Dockerfile
└── pyproject.toml
```
