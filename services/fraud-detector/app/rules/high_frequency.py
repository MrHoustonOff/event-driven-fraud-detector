from datetime import timedelta

from .base import FraudRule, TransactionContext


class HighFrequencyRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        if not ctx.history:
            return 0
        cutoff = ctx.tx.created_at - timedelta(minutes=60)
        recent = sum(1 for tx in ctx.history if tx.created_at >= cutoff)
        return 25 if recent > 5 else 0
