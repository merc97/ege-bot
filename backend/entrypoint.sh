#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Importing questions if needed..."
python -m app.scripts.import_questions

echo "Starting backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
