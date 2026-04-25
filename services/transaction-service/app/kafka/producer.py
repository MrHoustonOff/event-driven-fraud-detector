from aiokafka import AIOKafkaProducer
from pydantic import BaseModel

from app.config import settings


class KafkaProducerManager:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers
        )
        await self._producer.start()

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def publish(self, topic: str, model: BaseModel):
        if not self._producer:
            raise RuntimeError("Producer is not started")
        value = model.model_dump_json().encode("utf-8")
        await self._producer.send_and_wait(topic, value=value)


producer_manager = KafkaProducerManager()
