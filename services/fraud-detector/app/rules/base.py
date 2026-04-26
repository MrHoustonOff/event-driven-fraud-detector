from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.schemas import TransactionEvent


@dataclass
class TransactionContext:
    tx: TransactionEvent
    history: list[TransactionEvent]


class FraudRule(ABC):
    @abstractmethod
    async def score(self, ctx: TransactionContext) -> int: ...
