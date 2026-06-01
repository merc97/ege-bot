from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline import faq_keyboard, back_to_menu_keyboard
from bot.utils.api_client import APIClient

router = Router()

FAQ_ITEMS = {
    "how": (
        "📋 <b>Как это работает?</b>\n\n"
        "1. Выбери экзамен (ЕГЭ/ОГЭ) и предмет\n"
        "2. Бот даёт задания из реальных экзаменов\n"
        "3. Ты отвечаешь — бот проверяет\n"
        "4. При ошибке получаешь AI-объяснение\n"
        "5. Следи за прогрессом в разделе «Мой прогресс»"
    ),
    "progress": (
        "📊 <b>Как считается прогресс?</b>\n\n"
        "• Точность = правильные / всего попыток\n"
        "• Слабые задания — те, где ты ошибаешься чаще 50%\n"
        "• Бот автоматически подбирает больше заданий по слабым темам\n"
        "• Прогресс хранится навсегда и не сбрасывается"
    ),
    "ai": (
        "🤖 <b>Что такое AI-объяснение?</b>\n\n"
        "При ошибке бот отправляет задание в языковую модель,\n"
        "которая объясняет ошибку и даёт подсказку за 2-3 предложения.\n\n"
        "• Бесплатно: 3 объяснения в день\n"
        "• Premium: без ограничений\n\n"
        "Повторные ошибки кешируются — ответ мгновенный."
    ),
    "premium": (
        "⭐ <b>Что даёт Premium-подписка?</b>\n\n"
        "• Неограниченные AI-объяснения ошибок\n"
        "• Приоритетная подборка слабых тем\n"
        "• Детальная аналитика по номерам заданий ЕГЭ\n\n"
        "<b>Стоимость:</b>\n"
        "• 150 Telegram Stars / месяц\n"
        "• 149 ₽ / месяц (карта, СБП)\n\n"
        "<i>Оплата через /subscribe</i>"
    ),
    "support": (
        "📞 <b>Поддержка</b>\n\n"
        "Если что-то не работает или есть вопросы:\n"
        "@ege_bot_support\n\n"
        "<i>Отвечаем в течение 24 часов.</i>"
    ),
    "parent_how": (
        "👨‍👩‍👧 <b>Как работает режим родителя?</b>\n\n"
        "1. При регистрации выбери «Я родитель»\n"
        "2. Попроси ребёнка открыть бот → ⚙️ Настройки → Мой код\n"
        "3. Введи код ребёнка — аккаунты будут привязаны\n"
        "4. В <b>Панели ученика</b> ты видишь весь его прогресс и историю ответов в реальном времени"
    ),
    "parent_pay": (
        "💳 <b>Как оплатить Premium ребёнку?</b>\n\n"
        "Перейди в <b>Панель ученика → ⭐ Оплатить Premium ребёнку</b>.\n\n"
        "Оплата через Telegram Stars (150 ⭐/мес).\n"
        "Premium активируется на аккаунте ребёнка автоматически.\n\n"
        "<i>Звёзды можно купить прямо в Telegram.</i>"
    ),
    "parent_link": (
        "🔗 <b>Как привязать / сменить ученика?</b>\n\n"
        "• Каждый ученик имеет уникальный <b>код</b> (8 символов)\n"
        "• Узнать код: бот ученика → ⚙️ Настройки → Мой код\n"
        "• Сменить ученика: ⚙️ Настройки → Привязать ученика\n\n"
        "<i>К одному родителю можно привязать только одного ученика.</i>"
    ),
}


def faq_keyboard_for_role(role: str) -> object:
    builder = InlineKeyboardBuilder()
    if role == "parent":
        builder.button(text="👨‍👩‍👧 Как это работает?", callback_data="faq:parent_how")
        builder.button(text="💳 Оплата Premium ребёнку", callback_data="faq:parent_pay")
        builder.button(text="🔗 Привязка / смена ученика", callback_data="faq:parent_link")
        builder.button(text="📞 Поддержка", callback_data="faq:support")
    else:
        builder.button(text="📋 Как это работает?", callback_data="faq:how")
        builder.button(text="📊 Как считается прогресс?", callback_data="faq:progress")
        builder.button(text="🤖 Что такое AI-объяснение?", callback_data="faq:ai")
        builder.button(text="⭐ Что даёт подписка?", callback_data="faq:premium")
        builder.button(text="📞 Поддержка", callback_data="faq:support")
    builder.button(text="🔙 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "menu:faq")
async def show_faq(callback: CallbackQuery, api: APIClient):
    user = await api.get_user(callback.from_user.id)
    role = (user or {}).get("role", "student")
    await callback.message.edit_text(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыбери тему:",
        reply_markup=faq_keyboard_for_role(role),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq:"))
async def faq_item(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = FAQ_ITEMS.get(key, "Раздел не найден.")

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="menu:faq")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.message(Command("faq"))
async def cmd_faq(message: Message, api: APIClient):
    user = await api.get_user(message.from_user.id)
    role = (user or {}).get("role", "student")
    await message.answer(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыбери тему:",
        reply_markup=faq_keyboard_for_role(role),
        parse_mode="HTML",
    )
