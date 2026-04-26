.PHONY: up down build logs ps test clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	uv run pytest tests/test_full_pipeline.py -v

clean:
	docker compose down -v
