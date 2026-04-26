import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserLimit(Base):
    __tablename__ = "user_limits"
    __table_args__ = {"schema": "limits"}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("100000.00"))
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("500000.00"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpendingLog(Base):
    __tablename__ = "spending_log"
    __table_args__ = {"schema": "limits"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    """Minimal model — only fields needed for status UPDATE."""
    __tablename__ = "transactions"
    __table_args__ = {"schema": "transactions"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
