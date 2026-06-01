from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key
from app.database import get_session
from app.schemas.user import UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class ActivateRequest(BaseModel):
    telegram_id: int
    provider: str
    payment_id: str
    amount: int
    currency: str = "XTR"
    days: int = 30


@router.post("/activate", response_model=UserOut, dependencies=[Depends(verify_api_key)])
async def activate_subscription(
    body: ActivateRequest,
    db: AsyncSession = Depends(get_session),
):
    svc = UserService(db)
    try:
        user = await svc.activate_subscription(
            telegram_id=body.telegram_id,
            provider=body.provider,
            payment_id=body.payment_id,
            amount=body.amount,
            currency=body.currency,
            days=body.days,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return user
