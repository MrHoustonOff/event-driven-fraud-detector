from .base import FraudRule, TransactionContext


class LargeAmountRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        amount = ctx.tx.amount
        if amount > 30_000:
            return 30
        if amount > 10_000:
            return 10
        return 0
