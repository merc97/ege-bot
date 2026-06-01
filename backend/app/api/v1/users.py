from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.database import get_session
from app.models.session import SessionAnswer
from app.models.user import User
from app.schemas.user import UserOut, UserRegister, UserOnboarding
from app.schemas.session import HistoryOut, AnswerHistoryItem
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserOut, dependencies=[Depends(verify_api_key)])
async def register(data: UserRegister, db: AsyncSession = Depends(get_session)):
    svc = UserService(db)
    user, _ = await svc.register_or_update(data)
    return user


@router.get("/{telegram_id}", response_model=UserOut, dependencies=[Depends(verify_api_key)])
async def get_user(telegram_id: int, db: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException
    svc = UserService(db)
    user = await svc.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{telegram_id}/onboarding", response_model=UserOut, dependencies=[Depends(verify_api_key)])
async def complete_onboarding(
    telegram_id: int,
    data: UserOnboarding,
    db: AsyncSession = Depends(get_session),
):
    svc = UserService(db)
    return await svc.complete_onboarding(telegram_id, data)


@router.get("/{telegram_id}/history", response_model=HistoryOut, dependencies=[Depends(verify_api_key)])
async def get_history(
    telegram_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_session),
):
    from fastapi import HTTPException
    user = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base = (
        select(SessionAnswer)
        .join(User, User.id == SessionAnswer.session_id.in_(
            select(User.id)  # rewritten below
        ))
    )
    # Subquery: session_ids belonging to this user
    from app.models.session import TestSession
    user_session_ids = select(TestSession.id).where(TestSession.user_id == user.id)

    total_q = await db.execute(
        select(func.count(SessionAnswer.id)).where(SessionAnswer.session_id.in_(user_session_ids))
    )
    total = total_q.scalar_one()

    rows = await db.execute(
        select(SessionAnswer)
        .where(SessionAnswer.session_id.in_(user_session_ids))
        .order_by(SessionAnswer.answered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = rows.scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)
    return HistoryOut(
        items=[AnswerHistoryItem.model_validate(i) for i in items],
        total=total,
        page=page,
        pages=pages,
    )
