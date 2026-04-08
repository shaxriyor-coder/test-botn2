"""
Bot haqida handler
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.keyboards import about_inline_keyboard, main_menu_keyboard
from app.config import config

router = Router(name="about")


@router.message(F.text == "ℹ️ Biz haqimizda")
async def show_about(message: Message):
    about_text = (
        "🤖 <b>Test Bot</b>\n\n"
        "Bu bot orqali siz testlarni onlayn topshirishingiz va natijalarni tez ko'rishingiz mumkin.\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "👨‍💻 <b>Developer:</b>\n"
        "└ @Shaxriyor_Egamberdiyev\n\n"
        "🏢 <b>Dasturchi jamoa:</b>\n"
        "└ <b>LeaderSoft Team</b>\n\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "💡 <i>Professional dasturiy yechimlar </i>\n\n"
        "📌 <b>Xizmatlarimiz:</b>\n"
        "• Telegram botlar \n"
        "• Web dasturlash\n"
        "• Mobil ilovalar\n"
        "• IT konsalting\n\n"
        "📞 <b>Bog'lanish:</b> @Shaxriyor_Egamberdiyev"
    )
    
    await message.answer(
        about_text,
        reply_markup=about_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = config.is_admin(callback.from_user.id)
    
    await callback.message.edit_text(
        "Asosiy menyu:"
    )
    
    await callback.message.answer(
        "Tanlang:",
        reply_markup=main_menu_keyboard(is_admin)
    )
    
    await callback.answer()