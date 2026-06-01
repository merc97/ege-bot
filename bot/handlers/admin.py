from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.utils.api_client import APIClient

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, api: APIClient):
    if not is_admin(message.from_user.id):
        return
    stats = await api.get_admin_stats()
    text = (
        "🛠 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{stats['users_total']}</b>\n"
        f"⭐ Premium: <b>{stats['users_premium']}</b>\n"
        f"📋 Заданий в базе: <b>{stats['tasks_total']}</b>\n"
        f"📝 Сессий всего: <b>{stats['sessions_total']}</b>\n\n"
        "Команды:\n"
        "/grant @user 30 — выдать premium на N дней\n"
        "/broadcast — рассылка (Sprint 6)"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("grant"))
async def cmd_grant(message: Message, api: APIClient):
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Использование: /grant <telegram_id> [days=30]")
        return
    try:
        tg_id = int(parts[1].lstrip("@"))
        days = int(parts[2]) if len(parts) > 2 else 30
    except ValueError:
        await message.answer("Неверный формат. Пример: /grant 123456789 30")
        return
    await api.grant_premium(tg_id, days)
    await message.answer(f"✅ Premium выдан пользователю {tg_id} на {days} дней.")


@router.message(Command("stats"))
async def cmd_stats(message: Message, api: APIClient):
    if not is_admin(message.from_user.id):
        return
    await cmd_admin(message, api)
