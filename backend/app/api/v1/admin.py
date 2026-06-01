from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json

from app.api.deps import verify_api_key
from app.database import get_session
from app.models.user import User
from app.models.task import Task
from app.models.session import TestSession
from app.schemas.task import TaskImport
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.schemas.user import UserOnboarding

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", dependencies=[Depends(verify_api_key)])
async def get_stats(db: AsyncSession = Depends(get_session)):
    users_total = (await db.execute(select(func.count(User.id)))).scalar_one()
    users_premium = (await db.execute(
        select(func.count(User.id)).where(User.subscription_type == "premium")
    )).scalar_one()
    tasks_total = (await db.execute(select(func.count(Task.id)).where(Task.is_active.is_(True)))).scalar_one()
    sessions_total = (await db.execute(select(func.count(TestSession.id)))).scalar_one()
    return {
        "users_total": users_total,
        "users_premium": users_premium,
        "tasks_total": tasks_total,
        "sessions_total": sessions_total,
    }


@router.post("/tasks/import", dependencies=[Depends(verify_api_key)])
async def import_tasks(file: UploadFile = File(...), db: AsyncSession = Depends(get_session)):
    content = await file.read()
    items_raw = json.loads(content)
    items = [TaskImport(**item) for item in items_raw]
    svc = TaskService(db)
    count = await svc.import_tasks(items)
    return {"imported": count, "total": len(items)}


@router.post("/grant/{telegram_id}", dependencies=[Depends(verify_api_key)])
async def grant_premium(telegram_id: int, days: int = 30, db: AsyncSession = Depends(get_session)):
    from datetime import datetime, timedelta
    from sqlalchemy import update
    await db.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(
            subscription_type="premium",
            subscription_end=datetime.utcnow() + timedelta(days=days),
        )
    )
    await db.commit()
    return {"ok": True, "days": days}
