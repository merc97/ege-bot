from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.database import get_session
from app.schemas.task import TaskOut
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/next", response_model=TaskOut | None, dependencies=[Depends(verify_api_key)])
async def get_next_task(
    user_id: int = Query(...),
    subject: str = Query(...),
    exam_type: str = Query(...),
    session_id: int = Query(...),
    db: AsyncSession = Depends(get_session),
):
    svc = TaskService(db)
    return await svc.get_next(user_id, subject, exam_type, session_id)


@router.get("/{task_id}", response_model=TaskOut, dependencies=[Depends(verify_api_key)])
async def get_task(task_id: int, db: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    svc = TaskService(db)
    task = await svc.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
