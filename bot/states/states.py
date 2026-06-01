from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_exam = State()
    choosing_subjects = State()


class TestStates(StatesGroup):
    choosing_subject = State()
    choosing_exam_type = State()
    choosing_mode = State()
    in_progress = State()
