from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import faq_keyboard, back_to_menu_keyboard

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
        "При ошибке бот отправляет задание в языковую модель (Qwen 2.5),\n"
        "которая объясняет твою ошибку и даёт подсказку — за 2-3 предложения.\n\n"
        "• Бесплатно: 3 объяснения в день\n"
        "• Premium: без ограничений\n\n"
        "Повторные ошибки на одно задание кешируются — ответ мгновенный."
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
        "Напиши нам — @ege_bot_support\n\n"
        "<i>Отвечаем в течение 24 часов.</i>"
    ),
}


@router.callback_query(F.data == "menu:faq")
async def show_faq(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыбери тему:",
        reply_markup=faq_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq:"))
async def faq_item(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    text = FAQ_ITEMS.get(key, "Раздел не найден.")
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await message.answer(
        "❓ <b>Часто задаваемые вопросы</b>\n\nВыбери тему:",
        reply_markup=faq_keyboard(),
        parse_mode="HTML",
    )
