from .base import FraudRule, TransactionContext


class FraudEngine:
    def __init__(self, rules: list[FraudRule]) -> None:
        self.rules = rules

    async def evaluate(self, ctx: TransactionContext) -> tuple[int, list[str]]:
        triggered: list[str] = []
        total = 0
        for rule in self.rules:
            s = await rule.score(ctx)
            if s > 0:
                total += s
                triggered.append(rule.__class__.__name__)
        return min(total, 100), triggered
