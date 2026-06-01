from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.database import get_session
from app.schemas.user import UserOut, UserRegister, UserOnboarding
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
