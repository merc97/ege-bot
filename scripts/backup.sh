#!/bin/bash
set -euo pipefail

COMPOSE_DIR="/home/lexa/ege-bot"
BACKUP_DIR="/var/backups/ege-bot"
KEEP_DAYS=7
DATE=$(date +%Y-%m-%d)
FILE="$BACKUP_DIR/ege_bot_$DATE.sql.gz"
LOG_TAG="ege-bot-backup"

mkdir -p "$BACKUP_DIR"

cd "$COMPOSE_DIR"

# pg_dump через docker compose
docker compose exec -T postgres \
    pg_dump -U ege ege_bot | gzip > "$FILE"

SIZE=$(du -sh "$FILE" | cut -f1)
logger -t "$LOG_TAG" "Backup OK: $FILE ($SIZE)"

# Ротация: удалить бэкапы старше KEEP_DAYS дней
find "$BACKUP_DIR" -name "ege_bot_*.sql.gz" -mtime +$KEEP_DAYS -delete
logger -t "$LOG_TAG" "Rotation done (keep ${KEEP_DAYS} days)"
