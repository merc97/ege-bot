from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserRegister(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None


class UserOnboarding(BaseModel):
    selected_exam: str
    selected_subjects: list[str]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str
    subscription_type: str
    subscription_end: datetime | None
    onboarding_done: bool
    selected_exam: str | None
    selected_subjects: list[str] | None
    created_at: datetime
