import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    user_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=1, max_length=100)
    merchant: str = Field(min_length=1, max_length=255)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: int
    amount: Decimal
    currency: str
    country: str
    city: str
    merchant: str
    status: str
    fraud_score: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
