import random
import string
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import User
from app.models.progress import Subscription
from app.schemas.user import UserRegister, UserOnboarding


def _gen_referral() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def register_or_update(self, data: UserRegister) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(data.telegram_id)
        is_new = user is None

        if is_new:
            user = User(
                telegram_id=data.telegram_id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                referral_code=_gen_referral(),
            )
            self.db.add(user)
        else:
            user.username = data.username
            user.first_name = data.first_name
            user.last_name = data.last_name
            user.last_active_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(user)
        return user, is_new

    async def complete_onboarding(self, telegram_id: int, data: UserOnboarding) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        user.role = data.role
        if data.selected_exam is not None:
            user.selected_exam = data.selected_exam
        if data.selected_subjects is not None:
            user.selected_subjects = data.selected_subjects
        user.onboarding_done = True
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def link_parent_to_student(self, parent_telegram_id: int, student_code: str) -> User:
        parent = await self.get_by_telegram_id(parent_telegram_id)
        if not parent:
            raise ValueError("Parent not found")
        result = await self.db.execute(select(User).where(User.referral_code == student_code.upper().strip()))
        student = result.scalar_one_or_none()
        if not student:
            raise ValueError("Student code not found")
        if student.telegram_id == parent.telegram_id:
            raise ValueError("Cannot link to yourself")
        parent.linked_student_id = student.id
        parent.parent_linked_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(parent)
        return parent

    async def get_linked_student(self, parent_telegram_id: int) -> User | None:
        parent = await self.get_by_telegram_id(parent_telegram_id)
        if not parent or not parent.linked_student_id:
            return None
        return await self.db.get(User, parent.linked_student_id)

    async def can_use_ai(self, user: User) -> bool:
        if user.subscription_type == "premium":
            return True
        now = datetime.utcnow()
        if user.daily_ai_reset_at is None or (now - user.daily_ai_reset_at).days >= 1:
            await self.db.execute(
                update(User)
                .where(User.id == user.id)
                .values(daily_ai_used=0, daily_ai_reset_at=now)
            )
            await self.db.commit()
            return True
        return user.daily_ai_used < 3

    async def increment_ai_usage(self, user_id: int) -> None:
        await self.db.execute(
            update(User).where(User.id == user_id).values(daily_ai_used=User.daily_ai_used + 1)
        )
        await self.db.commit()

    async def activate_subscription(
        self,
        telegram_id: int,
        provider: str,
        payment_id: str,
        amount: int,
        currency: str = "XTR",
        days: int = 30,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")

        now = datetime.utcnow()
        expires_at = now + timedelta(days=days)

        await self.db.execute(
            update(User)
            .where(User.id == user.id)
            .values(subscription_type="premium", subscription_end=expires_at)
        )
        self.db.add(Subscription(
            user_id=user.id,
            plan="premium",
            provider=provider,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            started_at=now,
            expires_at=expires_at,
            status="active",
        ))
        await self.db.commit()
        await self.db.refresh(user)
        return user
