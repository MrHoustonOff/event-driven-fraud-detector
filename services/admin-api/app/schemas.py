import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FraudRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    weight: int = Field(ge=0, le=100)
    config_json: dict | None = None
    is_active: bool = True


class FraudRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    weight: int | None = Field(default=None, ge=0, le=100)
    config_json: dict | None = None
    is_active: bool | None = None


class FraudRuleResponse(BaseModel):
    id: int
    name: str
    weight: int
    config_json: dict | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLimitUpdate(BaseModel):
    daily_limit: Decimal | None = Field(default=None, gt=0)
    monthly_limit: Decimal | None = Field(default=None, gt=0)


class UserLimitResponse(BaseModel):
    user_id: int
    daily_limit: Decimal
    monthly_limit: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopTransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: int
    amount: Decimal
    status: str
    fraud_score: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    transactions_today: int
    alerts_today: int
    blocked_today: int
    top_fraud_score: list[TopTransactionResponse]
