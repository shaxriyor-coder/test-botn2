import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config
from app.db import Database
from app.middlewares import DatabaseMiddleware, LoggingMiddleware, UserRegistrationMiddleware
from app.handlers import get_routers  


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Bot ishga tushmoqda...")
    
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    db = Database()
    await db.connect()
    
    dp.message.middleware(DatabaseMiddleware(db))
    dp.callback_query.middleware(DatabaseMiddleware(db))
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(UserRegistrationMiddleware())
    
    for router in get_routers():
        dp.include_router(router)
    
    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
    logger.info(f"👨‍💼 Adminlar: {config.bot.admin_ids}")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.disconnect()
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi!")