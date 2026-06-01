.PHONY: up down build logs migrate import-questions shell-backend shell-bot psql backup help

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

backup:
	sudo /home/lexa/ege-bot/scripts/backup.sh

# First deploy
init: build up migrate import-questions
	@echo "✅ EGE Bot is ready!"

help:
	@echo "EGE Bot — команды:"
	@echo "  make init              — первый запуск (build+up+migrate+import)"
	@echo "  make up/down/build     — управление контейнерами"
	@echo "  make logs              — логи всех контейнеров"
	@echo "  make logs-bot          — логи бота"
	@echo "  make logs-backend      — логи бэкенда"
	@echo "  make migrate           — запустить миграции alembic"
	@echo "  make import-questions  — загрузить задания из data/questions/"
	@echo "  make backup            — ручной бэкап БД"
	@echo "  make psql              — подключиться к PostgreSQL"
	@echo "  make restart-bot       — рестарт контейнера бота"
	@echo "  make restart-backend   — рестарт контейнера бэкенда"
