from decimal import Decimal

from pydantic import BaseModel, Field


class LimitsResponse(BaseModel):
    user_id: int
    daily_limit: Decimal
    monthly_limit: Decimal
    spent_today: Decimal
    spent_this_month: Decimal


class LimitsUpdate(BaseModel):
    daily_limit: Decimal | None = Field(default=None, gt=0)
    monthly_limit: Decimal | None = Field(default=None, gt=0)
