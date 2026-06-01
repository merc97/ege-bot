from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.api.deps import verify_api_key
from app.database import get_session, get_redis
from app.models.user import User
from app.schemas.session import SessionCreate, SessionOut, AnswerSubmit, AnswerResult, ProgressOut
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.services.progress_service import ProgressService
from sqlalchemy import select

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionOut, dependencies=[Depends(verify_api_key)])
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    user_svc = UserService(db)
    user = await user_svc.get_by_telegram_id(data.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    svc = SessionService(db, redis)
    return await svc.create(user.id, data.subject, data.exam_type, data.mode)


@router.post("/{session_id}/answer", response_model=AnswerResult, dependencies=[Depends(verify_api_key)])
async def submit_answer(
    session_id: int,
    body: AnswerSubmit,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    svc = SessionService(db, redis)
    return await svc.submit_answer(
        session_id=session_id,
        task_id=body.task_id,
        user_answer=body.user_answer,
        time_spent=body.time_spent,
        want_ai=body.want_ai,
    )


@router.post("/{session_id}/finish", response_model=SessionOut, dependencies=[Depends(verify_api_key)])
async def finish_session(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    svc = SessionService(db, redis)
    return await svc.finish(session_id)


@router.get("/progress/{telegram_id}", response_model=ProgressOut, dependencies=[Depends(verify_api_key)])
async def get_progress(telegram_id: int, db: AsyncSession = Depends(get_session)):
    svc = ProgressService(db)
    result = await svc.get_summary(telegram_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result
