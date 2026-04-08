import asyncio
import logging

from app.config import config
from aiogram import Bot


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=config.bot.token)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook o'chirildi va pending updates tozalandi")
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
