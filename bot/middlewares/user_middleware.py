from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.utils.api_client import APIClient


class UserMiddleware(BaseMiddleware):
    """Registers/updates user in backend on every update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        api: APIClient = data.get("api")
        if user and api:
            try:
                await api.register_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
            except Exception:
                pass
        return await handler(event, data)
