.PHONY: up down build logs migrate import-questions shell-backend shell-bot psql

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f --tail=100

logs-bot:
	docker compose logs -f bot --tail=100

logs-backend:
	docker compose logs -f backend --tail=100

migrate:
	docker compose exec backend alembic upgrade head

import-questions:
	docker compose exec backend python -m app.scripts.import_questions

shell-backend:
	docker compose exec backend bash

shell-bot:
	docker compose exec bot bash

psql:
	docker compose exec postgres psql -U ege ege_bot

restart-bot:
	docker compose restart bot

restart-backend:
	docker compose restart backend

# First deploy
init: build up migrate import-questions
	@echo "✅ EGE Bot is ready!"
