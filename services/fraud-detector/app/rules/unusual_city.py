from .base import FraudRule, TransactionContext

_HISTORY_WINDOW = 30


class UnusualCityRule(FraudRule):
    async def score(self, ctx: TransactionContext) -> int:
        if not ctx.history:
            return 0
        known = {tx.city for tx in ctx.history[-_HISTORY_WINDOW:]}
        return 20 if ctx.tx.city not in known else 0
