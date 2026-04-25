CREATE SCHEMA transactions;
CREATE SCHEMA fraud;
CREATE SCHEMA limits;
CREATE SCHEMA notify;
CREATE SCHEMA auth;

-- -------------------------------------------------------
-- transactions.transactions
-- -------------------------------------------------------
CREATE TABLE transactions.transactions (
    id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     INTEGER       NOT NULL,
    amount      NUMERIC(15,2) NOT NULL,
    currency    VARCHAR(3)    NOT NULL DEFAULT 'RUB',
    country     CHAR(2)       NOT NULL,
    city        VARCHAR(100)  NOT NULL,
    merchant    VARCHAR(255)  NOT NULL,
    status      VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    fraud_score INTEGER,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tx_user_created ON transactions.transactions(user_id, created_at DESC);
CREATE INDEX idx_tx_status       ON transactions.transactions(status);

-- -------------------------------------------------------
-- fraud.rules
-- -------------------------------------------------------
CREATE TABLE fraud.rules (
    id          SERIAL       PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    weight      INTEGER      NOT NULL CHECK (weight >= 0 AND weight <= 100),
    config_json JSONB,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- limits.user_limits
-- -------------------------------------------------------
CREATE TABLE limits.user_limits (
    user_id       INTEGER       PRIMARY KEY,
    daily_limit   NUMERIC(15,2) NOT NULL DEFAULT 100000.00,
    monthly_limit NUMERIC(15,2) NOT NULL DEFAULT 500000.00,
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- limits.spending_log
-- -------------------------------------------------------
CREATE TABLE limits.spending_log (
    id             SERIAL        PRIMARY KEY,
    user_id        INTEGER       NOT NULL,
    amount         NUMERIC(15,2) NOT NULL,
    transaction_id UUID          NOT NULL UNIQUE,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_spending_user_date ON limits.spending_log(user_id, created_at DESC);

-- -------------------------------------------------------
-- notify.notifications
-- -------------------------------------------------------
CREATE TABLE notify.notifications (
    id            SERIAL      PRIMARY KEY,
    user_id       INTEGER     NOT NULL,
    type          VARCHAR(50) NOT NULL,
    payload       JSONB       NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'sent',
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- auth.users
-- -------------------------------------------------------
CREATE TABLE auth.users (
    id            SERIAL      PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(60) NOT NULL,
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
