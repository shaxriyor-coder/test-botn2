
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Message, CallbackQuery

from app.db import Database

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
   
    
    def __init__(self, db: Database):
        self.db = db
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
        
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")

        if user:
            info = f"User {user.id} (@{user.username}) - Event: {event.__class__.__name__}"
            if isinstance(event, Message):
                info += f" - text: {event.text!r}"
            elif isinstance(event, CallbackQuery):
                info += f" - callback_data: {event.data!r}"

            logger.info(info)
        
        return await handler(event, data)


class UserRegistrationMiddleware(BaseMiddleware):

    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        db: Database = data.get("db")
        
        if user and db:
            db_user = await db.get_user(user.id)
            if not db_user:
                await db.create_user(user.id)
                logger.info(f"New user registered: {user.id}")
        
        return await handler(event, data)