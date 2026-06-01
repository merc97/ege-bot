from pydantic import BaseModel, ConfigDict


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    exam_type: str
    topic: str | None
    task_number: int | None
    difficulty: int
    question_text: str
    options: dict | None
    hint: str | None


class TaskImport(BaseModel):
    subject: str
    exam_type: str
    topic: str | None = None
    task_number: int | None = None
    difficulty: int = 1
    question_text: str
    options: dict | None = None
    correct_answer: str
    hint: str | None = None
    source_url: str | None = None
    source_id: str | None = None
