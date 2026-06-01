import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import settings
from bot.handlers import start, test, progress, faq, admin, subscribe, history, parent
from bot.handlers import settings as settings_handler
from bot.middlewares.user_middleware import UserMiddleware
from bot.utils.api_client import APIClient

logging.basicConfig(
    level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    api = APIClient(base_url=settings.BACKEND_URL, api_key=settings.API_KEY)

    dp["api"] = api
    dp.update.middleware(UserMiddleware())

    dp.include_router(start.router)
    dp.include_router(test.router)
    dp.include_router(progress.router)
    dp.include_router(history.router)
    dp.include_router(parent.router)
    dp.include_router(faq.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin.router)
    dp.include_router(subscribe.router)

    logger.info("Starting EGE Bot (@ege777_bot)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
