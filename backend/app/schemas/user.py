from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserRegister(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None


class UserOnboarding(BaseModel):
    role: str = "student"
    selected_exam: str | None = None
    selected_subjects: list[str] | None = None


class LinkStudentRequest(BaseModel):
    student_code: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str
    role: str
    linked_student_id: int | None
    subscription_type: str
    subscription_end: datetime | None
    onboarding_done: bool
    selected_exam: str | None
    selected_subjects: list[str] | None
    referral_code: str | None
    created_at: datetime
