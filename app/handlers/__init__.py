
from aiogram import Router

from app.handlers import common, registration, admin, about


def get_routers() -> list[Router]:
    """Barcha routerlarni olish"""
    return [
        registration.router, 
        admin.router,         
        about.router,       
        common.router,       
    ]