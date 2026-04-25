from .base import FraudRule, TransactionContext


class NewCountryRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        if not ctx.history:
            return 0
        known = {tx.country for tx in ctx.history}
        return 40 if ctx.tx.country not in known else 0
