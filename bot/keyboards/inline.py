from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

SUBJECTS = {
    "math": "📐 Математика",
    "russian": "📝 Русский язык",
    "physics": "⚡ Физика",
    "chemistry": "🧪 Химия",
    "biology": "🌿 Биология",
    "history": "🏛 История",
    "social": "🤝 Обществознание",
    "english": "🇬🇧 Английский",
    "informatics": "💻 Информатика",
}

EGE_SUBJECTS = ["math", "russian", "physics", "chemistry", "biology", "history", "social", "english", "informatics"]
OGE_SUBJECTS = ["math", "russian", "physics", "chemistry", "biology", "history", "social", "english", "informatics"]


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Начать тест", callback_data="menu:test")
    builder.button(text="📊 Мой прогресс", callback_data="menu:progress")
    builder.button(text="⚙️ Настройки", callback_data="menu:settings")
    builder.button(text="❓ FAQ", callback_data="menu:faq")
    builder.button(text="⭐ Подписка", callback_data="menu:subscribe")
    builder.adjust(2)
    return builder.as_markup()


def exam_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📘 ЕГЭ", callback_data="onboard:exam:ege")
    builder.button(text="📗 ОГЭ", callback_data="onboard:exam:oge")
    builder.adjust(2)
    return builder.as_markup()


def subjects_keyboard(exam_type: str = "ege", selected: list[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or []
    available = EGE_SUBJECTS if exam_type == "ege" else OGE_SUBJECTS
    builder = InlineKeyboardBuilder()
    for key in available:
        mark = "✅ " if key in selected else ""
        builder.button(text=f"{mark}{SUBJECTS[key]}", callback_data=f"subject:{key}")
    builder.button(text="➡️ Далее", callback_data="subject:done")
    builder.adjust(2)
    return builder.as_markup()


def test_subject_keyboard(exam_type: str, subjects: list[str] | None = None) -> InlineKeyboardMarkup:
    available = subjects or (EGE_SUBJECTS if exam_type == "ege" else OGE_SUBJECTS)
    builder = InlineKeyboardBuilder()
    for key in available:
        builder.button(text=SUBJECTS.get(key, key), callback_data=f"test:subject:{key}")
    builder.button(text="🔙 Назад", callback_data="menu:test")
    builder.adjust(2)
    return builder.as_markup()


def test_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Практика", callback_data="mode:practice")
    builder.button(text="🎯 Мини-экзамен (10 вопросов)", callback_data="mode:exam")
    builder.adjust(1)
    return builder.as_markup()


def answer_options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key in options:
        builder.button(text=key, callback_data=f"test:answer:{key}")
    builder.adjust(len(options))
    return builder.as_markup()


def next_question_keyboard(is_last: bool, session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_last:
        builder.button(text="➡️ Следующий вопрос", callback_data=f"test:next:{session_id}")
    builder.button(text="🏁 Завершить", callback_data=f"test:finish:{session_id}")
    builder.adjust(1)
    return builder.as_markup()


def faq_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Как это работает?", callback_data="faq:how")
    builder.button(text="📊 Как считается прогресс?", callback_data="faq:progress")
    builder.button(text="🤖 Что такое AI-объяснение?", callback_data="faq:ai")
    builder.button(text="⭐ Что даёт подписка?", callback_data="faq:premium")
    builder.button(text="📞 Написать в поддержку", callback_data="faq:support")
    builder.button(text="🔙 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def subscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить за Telegram Stars (150 ⭐/мес)", callback_data="pay:stars")
    builder.button(text="💳 Оплатить картой (149 ₽/мес)", callback_data="pay:yookassa")
    builder.button(text="🔙 Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Главное меню", callback_data="menu:main")
    return builder.as_markup()
