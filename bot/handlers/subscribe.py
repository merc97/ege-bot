import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

from bot.keyboards.inline import subscribe_keyboard, back_to_menu_keyboard, main_menu_keyboard
from bot.utils.api_client import APIClient

router = Router()
logger = logging.getLogger(__name__)

PREMIUM_PRICE_STARS = 150
PREMIUM_PRICE_RUB = 149


@router.callback_query(F.data == "menu:subscribe")
async def show_subscribe(callback: CallbackQuery):
    await callback.message.edit_text(
        "⭐ <b>Premium-подписка</b>\n\n"
        "Безлимитные AI-объяснения + аналитика по слабым темам.\n\n"
        f"• <b>{PREMIUM_PRICE_STARS} Telegram Stars</b> / месяц\n"
        f"• <b>{PREMIUM_PRICE_RUB} ₽</b> / месяц (карта, СБП)\n\n"
        "Выбери способ оплаты:",
        reply_markup=subscribe_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "pay:stars")
async def pay_stars(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer_invoice(
        title="EGE Bot Premium — 1 месяц",
        description="Безлимитные AI-объяснения ошибок, аналитика слабых тем",
        payload=f"premium_stars_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium 1 месяц", amount=PREMIUM_PRICE_STARS)],
    )


@router.callback_query(F.data == "pay:yookassa")
async def pay_yookassa(callback: CallbackQuery):
    await callback.answer(
        "Оплата картой будет доступна в ближайшее время. Пока используй Telegram Stars!",
        show_alert=True,
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, api: APIClient):
    payment = message.successful_payment
    telegram_id = message.from_user.id

    try:
        await api.activate_subscription(
            telegram_id=telegram_id,
            provider="stars",
            payment_id=payment.telegram_payment_charge_id,
            amount=payment.total_amount,
            currency=payment.currency,
            days=30,
        )
        await message.answer(
            "🎉 <b>Подписка активирована!</b>\n\n"
            "⭐ Premium на 30 дней подключён.\n"
            "Теперь тебе доступны безлимитные AI-объяснения ошибок!\n\n"
            "Удачи в подготовке 💪",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to activate subscription for user %d", telegram_id)
        await message.answer(
            "⚠️ Оплата прошла, но возникла ошибка активации.\n"
            "Напиши в поддержку — разберёмся в течение часа.",
            parse_mode="HTML",
        )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    await message.answer(
        "⭐ <b>Premium-подписка</b>\n\n"
        f"• {PREMIUM_PRICE_STARS} Telegram Stars / месяц\n"
        f"• {PREMIUM_PRICE_RUB} ₽ / месяц\n",
        reply_markup=subscribe_keyboard(),
        parse_mode="HTML",
    )
