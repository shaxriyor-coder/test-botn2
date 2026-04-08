from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)



def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📝 Test topshirish")],
        [KeyboardButton(text="🏆 O'rnimni ko'rish")],
        [KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="ℹ️ Biz haqimizda")],
    ]
    
    if is_admin:
        buttons.append([KeyboardButton(text="👨‍💼 Admin Panel")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def about_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="👨‍💻 Developer", url="https://t.me/Shaxriyor_Egamberdiyev")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
def admin_panel_keyboard():
    keyboard = [
        [KeyboardButton(text="📣 Kanallar"), KeyboardButton(text="🧪 Test yaratish")],
        [KeyboardButton(text="🧾 Testlar")],
        [KeyboardButton(text="➕ Foydalanuvchi qo'shish")],
        [KeyboardButton(text="📊 Natijalarni yuklab olish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def tests_management_keyboard():
    keyboard = [
        [KeyboardButton(text="📋 Testlar ro'yxati")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def tests_list_inline_keyboard(tests: list):

    
    keyboard = []
    for t in tests:
        keyboard.append([
            InlineKeyboardButton(text=f"❌ O'chirish {t.code}", callback_data=f"delete_test:{t.code}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def contact_keyboard():
    keyboard = [
        [KeyboardButton(text="📱 Kontaktni yuborish", request_contact=True)],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def contact_only_keyboard():
    keyboard = [
        [KeyboardButton(text="📱 Kontaktni yuborish", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard():
    keyboard = [[KeyboardButton(text="❌ Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def admin_user_confirm_keyboard():
    keyboard = [
        [KeyboardButton(text="✅ Yaratish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def only_back_reply_keyboard():
    keyboard = [[KeyboardButton(text="🔙 Orqaga")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)


def channels_management_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="remove_channel")],
        [InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="list_channels")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def subscription_check_keyboard(channels: list):
    keyboard = []
    
    for channel in channels:
        username = channel.username if hasattr(channel, 'username') else channel.get('username', '@channel')
        keyboard.append([InlineKeyboardButton(
            text=f"📢 {username}", 
            url=f"https://t.me/{username.lstrip('@')}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="✅ Obunani tekshirish", 
        callback_data="check_subscription"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def profile_keyboard():
    keyboard = [[InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_profile")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def rank_options_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="1️⃣ Qatnashgan testlarim", callback_data="my_tests")],
        [InlineKeyboardButton(text="2️⃣ Kod orqali qidirish", callback_data="search_by_code")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_button():
    keyboard = [[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)