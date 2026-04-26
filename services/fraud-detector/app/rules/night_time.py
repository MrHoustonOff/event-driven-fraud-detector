from datetime import timezone

from .base import FraudRule, TransactionContext

_NIGHT_START = 2
_NIGHT_END = 5  # exclusive: hours 2, 3, 4


class NightTimeRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        hour = ctx.tx.created_at.astimezone(timezone.utc).hour
        return 15 if _NIGHT_START <= hour < _NIGHT_END else 0
