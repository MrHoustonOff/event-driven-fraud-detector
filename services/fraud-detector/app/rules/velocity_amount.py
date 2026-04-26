from .base import FraudRule, TransactionContext


class VelocityAmountRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        if not ctx.history:
            return 0
        avg = sum(tx.amount for tx in ctx.history) / len(ctx.history)
        return 20 if ctx.tx.amount > avg * 3 else 0
