from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    kafka_bootstrap_servers: str = "kafka:9092"
    webhook_url: str

    model_config = {"env_file": ".env"}


settings = Settings()
