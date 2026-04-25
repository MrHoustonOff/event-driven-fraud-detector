from pydantic import BaseModel, UUID4, Field
from decimal import Decimal
from datetime import datetime
from enum import Enum


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"


class TransactionEvent(BaseModel):
    transaction_id: UUID4
    user_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=1, max_length=100)
    merchant: str = Field(min_length=1, max_length=255)
    created_at: datetime


class AlertEvent(BaseModel):
    transaction_id: UUID4
    user_id: int
    fraud_score: int = Field(ge=0, le=100)
    triggered_rules: list[str]
    created_at: datetime


class LimitExceededEvent(BaseModel):
    transaction_id: UUID4
    user_id: int
    limit_type: str = Field(pattern="^(daily|monthly)$")
    current_spent: Decimal
    limit_value: Decimal
    created_at: datetime
