import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.kafka.producer import producer_manager
from app.models import Transaction
from app.schemas import TransactionCreate, TransactionResponse
from shared.schemas import TransactionEvent

router = APIRouter(prefix="/transactions", tags=["Транзакции"])


@router.post(
    "",
    status_code=202,
    response_model=TransactionResponse,
    summary="Принять транзакцию",
    description="Валидирует данные, сохраняет транзакцию в БД со статусом **PENDING** и возвращает 202 Accepted. "
    "Анализ фрода и проверка лимитов происходят асинхронно.",
)
async def create_transaction(
    body: TransactionCreate,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    tx = Transaction(
        user_id=body.user_id,
        amount=body.amount,
        currency=body.currency,
        country=body.country,
        city=body.city,
        merchant=body.merchant,
    )
    session.add(tx)
    await session.commit()  # 1. сначала БД

    event = TransactionEvent(
        transaction_id=tx.id,
        user_id=tx.user_id,
        amount=tx.amount,
        currency=tx.currency,
        country=tx.country,
        city=tx.city,
        merchant=tx.merchant,
        created_at=tx.created_at,
    )
    await producer_manager.publish("tx.raw", event)  # 2. потом Kafka

    return TransactionResponse.model_validate(tx)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Получить статус транзакции",
    description="Возвращает текущий статус и данные транзакции по её UUID. "
    "Статус обновляется асинхронно сервисами fraud-detector и limits-service.",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    tx = await session.scalar(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    if tx is None:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")
    return TransactionResponse.model_validate(tx)
