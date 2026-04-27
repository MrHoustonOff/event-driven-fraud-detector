import random

from locust import HttpUser, between, task

_COUNTRIES = ["RU", "US", "DE", "TH"]
_COUNTRY_WEIGHTS = [85, 6, 5, 4]

_CITIES_BY_COUNTRY = {
    "RU": ["Moscow", "Saint Petersburg", "Kazan", "Novosibirsk"],
    "US": ["New York", "Los Angeles", "Chicago"],
    "DE": ["Berlin", "Munich", "Hamburg"],
    "TH": ["Bangkok", "Chiang Mai", "Phuket"],
}
_DEFAULT_CITY = ["Unknown"]

_MERCHANTS = ["Sbermarket", "Wildberries", "Ozon", "DNS", "Magnit", "Yandex.Eda"]
_FRAUD_COUNTRIES = ["TH", "AE", "CN"]
_FRAUD_CITIES = {"TH": "Bangkok", "AE": "Dubai", "CN": "Shanghai"}
_FRAUD_MERCHANTS = ["Casino Royal", "FX Exchange", "Crypto ATM"]


def _regular_payload(user_id: int) -> dict:
    country = random.choices(_COUNTRIES, weights=_COUNTRY_WEIGHTS)[0]
    city = random.choice(_CITIES_BY_COUNTRY.get(country, _DEFAULT_CITY))
    return {
        "user_id": user_id,
        "amount": str(round(random.uniform(100, 15_000), 2)),
        "currency": "RUB",
        "country": country,
        "city": city,
        "merchant": random.choice(_MERCHANTS),
    }


def _fraud_payload(user_id: int) -> dict:
    country = random.choice(_FRAUD_COUNTRIES)
    return {
        "user_id": user_id,
        "amount": str(round(random.uniform(30_000, 100_000), 2)),
        "currency": "RUB",
        "country": country,
        "city": _FRAUD_CITIES[country],
        "merchant": random.choice(_FRAUD_MERCHANTS),
    }


class RegularUser(HttpUser):
    weight = 9
    wait_time = between(0.5, 2)

    def on_start(self) -> None:
        self.user_id = random.randint(1, 1000)
        self._tx_ids: list[str] = []

    @task(4)
    def post_transaction(self) -> None:
        resp = self.client.post("/transactions", json=_regular_payload(self.user_id))
        if resp.status_code == 202:
            self._tx_ids.append(resp.json()["id"])
            if len(self._tx_ids) > 10:
                self._tx_ids.pop(0)

    @task(1)
    def get_transaction(self) -> None:
        if not self._tx_ids:
            return
        tx_id = random.choice(self._tx_ids)
        self.client.get(f"/transactions/{tx_id}", name="/transactions/[id]")


class FraudUser(HttpUser):
    weight = 1
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.user_id = random.randint(1001, 2000)

    @task
    def post_fraud_transaction(self) -> None:
        self.client.post(
            "/transactions",
            json=_fraud_payload(self.user_id),
            name="/transactions [fraud]",
        )
