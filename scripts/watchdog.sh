#!/bin/bash
set -euo pipefail

COMPOSE_DIR="/home/lexa/ege-bot"
SERVICE="ege-bot.service"
LOG_TAG="ege-bot-watchdog"

cd "$COMPOSE_DIR"

bot_status=$(docker compose ps --status running --quiet bot 2>/dev/null | wc -l)
backend_status=$(docker compose ps --status running --quiet backend 2>/dev/null | wc -l)

if [[ "$bot_status" -eq 0 || "$backend_status" -eq 0 ]]; then
    logger -t "$LOG_TAG" "bot=$bot_status backend=$backend_status — restarting $SERVICE"
    systemctl restart "$SERVICE"
else
    logger -t "$LOG_TAG" "OK bot=$bot_status backend=$backend_status"
fi
