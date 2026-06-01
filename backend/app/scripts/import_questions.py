"""Imports questions from JSON files in QUESTIONS_DIR if tasks table is empty."""
import asyncio
import json
import logging
import os
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.task import Task
from app.schemas.task import TaskImport
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


async def run() -> None:
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(Task.id)))).scalar_one()
        if count > 0:
            logger.info("Tasks already imported (%d tasks), skipping.", count)
            return

        questions_dir = Path(settings.QUESTIONS_DIR)
        if not questions_dir.exists():
            logger.warning("Questions dir %s not found, skipping import.", questions_dir)
            return

        svc = TaskService(db)
        total = 0
        for json_file in sorted(questions_dir.glob("*.json")):
            try:
                items_raw = json.loads(json_file.read_text(encoding="utf-8"))
                items = [TaskImport(**item) for item in items_raw]
                imported = await svc.import_tasks(items)
                logger.info("Imported %d tasks from %s", imported, json_file.name)
                total += imported
            except Exception as e:
                logger.error("Failed to import %s: %s", json_file.name, e)

        logger.info("Total imported: %d tasks", total)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    asyncio.run(run())
