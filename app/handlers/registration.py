
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.db import Database
from app.keyboards import contact_keyboard, main_menu_keyboard
from app.keyboards import only_back_reply_keyboard
from app.states import Registration, ProfileEdit, TestSolving
from app.utils import is_valid_name, is_valid_class
from app.config import config

router = Router(name="registration")


async def start_registration(message: Message, state: FSMContext, include_back: bool = True):
    """Ro'yxatdan o'tishni boshlash"""
    from app.keyboards import contact_only_keyboard
    kb = contact_keyboard() if include_back else contact_only_keyboard()
    await message.answer(
        "👋 Xush kelibsiz!\n\n"
        "Davom etish uchun profilingizni to'ldiring.\n\n"
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=kb
    )
    await state.update_data(contact_no_back=(not include_back), contact_prompted=False)
    await state.set_state(Registration.waiting_for_contact)


@router.message(Registration.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext, db: Database):
    phone = getattr(message.contact, 'phone_number', None)
    if not phone:
        await message.answer("❌ Kontaktda telefon raqami topilmadi. Iltimos, qayta yuboring.")
        return

    normalized_phone = db.normalize_phone(phone)
    await state.update_data(phone=normalized_phone)

    claimed = await db.claim_pre_registered_user(message.from_user.id, normalized_phone)

    if claimed:
        await message.answer(
            "✅ Siz uchun oldindan yaratilgan profil topildi va akkauntga bog'landi!",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        is_admin = config.is_admin(message.from_user.id)
        await message.answer(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin)
        )
        return
    
    await message.answer(
        "✅ Kontakt qabul qilindi!",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await message.answer(
        "👤 Ism Familiyangizni kiriting:\n\n"
        "Masalan: Shaxriyor Egamberdiyev"
    )
    
    await state.update_data(contact_no_back=False, contact_prompted=False)
    await state.set_state(Registration.waiting_for_name)


@router.message(Registration.waiting_for_contact)
async def contact_not_received(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    
    if txt == "🔙 Orqaga":
        await state.clear()
        is_admin = config.is_admin(message.from_user.id)
        await message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard(is_admin))
        return

    data = await state.get_data()
    
    if not data.get('contact_prompted'):
        if data.get('contact_no_back'):
            from app.keyboards import contact_only_keyboard
            kb = contact_only_keyboard()
        else:
            kb = contact_keyboard()
        
        await message.answer(
            "📱 Iltimos, <b>kontakt tugmasini</b> bosing va kontaktingizni yuboring.\n\n"
            "⚠️ Qo'lda yozish mumkin emas!",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await state.update_data(contact_prompted=True)


@router.message(Registration.waiting_for_name, F.text == "🔙 Orqaga")
async def back_from_name(message: Message, state: FSMContext):
    await state.clear()
    await start_registration(message, state, include_back=True)


@router.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    if not is_valid_name(name):
        await message.answer(
            "❌ Iltimos, to'liq ism familiyangizni kiriting!\n\n"
            "Masalan: Shaxriyor Egamberdiyev"
        )
        return
    
    await state.update_data(full_name=name)
    await message.answer("🏫 Sinfingizni kiriting:\n\nMasalan: 9-A yoki 11-B")
    await state.set_state(Registration.waiting_for_class)


@router.message(Registration.waiting_for_class, F.text == "🔙 Orqaga")
async def back_from_class(message: Message, state: FSMContext):
    """Sinfdan orqaga qaytish"""
    await message.answer(
        "👤 Ism Familiyangizni kiriting:\n\n"
        "Masalan: Shaxriyor Egamberdiyev"
    )
    await state.set_state(Registration.waiting_for_name)


@router.message(Registration.waiting_for_class)
async def process_class(message: Message, state: FSMContext, db: Database):
    class_name = message.text.strip()
    
    if not is_valid_class(class_name):
        await message.answer("❌ Noto'g'ri format!\n\nMasalan: 9-A, 11-B, 10")
        return
    
    try:
        data = await state.get_data()
        await db.update_user_profile(
            message.from_user.id,
            data['full_name'],
            data['phone'],
            class_name
        )
        
        await message.answer("✅ Profil muvaffaqiyatli saqlandi!")
        
        is_admin = config.is_admin(message.from_user.id)
        
        if 'pending_test_code' in data:
            test_code = data['pending_test_code']
            test = await db.get_test_by_code(test_code)
            
            if test:
                await message.answer(
                    f"📝 Test kodi: {test_code}\n"
                    f"📊 Savollar soni: {test.question_count}\n\n"
                    "Test savollarini quyida ko'rasiz 👇"
                )
                from app.utils import send_test_content
                await send_test_content(message, test.content)
                await message.answer(
                    f"✍️ Javoblarni formatda yuboring: 1a2b3c...\n"
                    f"⚠️ Barcha {test.question_count} ta savolga javob bering!"
                )
                await state.update_data(
                    active_test_id=test.id,
                    active_test_code=test_code
                )
                await state.set_state(TestSolving.waiting_for_answer)
            else:
                await state.clear()
                await message.answer(
                    "Asosiy menyu:",
                    reply_markup=main_menu_keyboard(is_admin)
                )
        else:
            await state.clear()
            await message.answer(
                "Asosiy menyu:",
                reply_markup=main_menu_keyboard(is_admin)
            )
            
    except Exception as e:
        print(f"Profile save error: {e}")
        await message.answer(
            "❌ Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.\n\n"
            "Agar muammo davom etsa, admin bilan bog'laning."
        )
        return


@router.callback_query(F.data == "edit_profile")
async def edit_profile_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✏️ Yangi ism familiyangizni kiriting:\n\nMasalan: Shaxriyor Egamberdiyev"
    )
    await state.set_state(ProfileEdit.waiting_for_name)
    await callback.answer()


@router.message(ProfileEdit.waiting_for_name)
async def edit_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    if not is_valid_name(name):
        await message.answer(
            "❌ Iltimos, to'liq ism familiyangizni kiriting!\n\nMasalan: Shaxriyor Egamberdiyev"
        )
        return
    
    await state.update_data(full_name=name)
    await message.answer("🏫 Yangi sinfingizni kiriting (masalan: 9-A):")
    await state.set_state(ProfileEdit.waiting_for_class)


@router.message(ProfileEdit.waiting_for_class)
async def edit_class(message: Message, state: FSMContext, db: Database):
    class_name = message.text.strip()
    
    if not is_valid_class(class_name):
        await message.answer("❌ Noto'g'ri format!\n\nMasalan: 9-A, 11-B, 10")
        return
    
    try:
        data = await state.get_data()
        user = await db.get_user(message.from_user.id)
        
        await db.update_user_profile(
            message.from_user.id,
            data['full_name'],
            user.phone,
            class_name
        )
        
        await message.answer("✅ Profil muvaffaqiyatli yangilandi!")
        
        updated_user = await db.get_user(message.from_user.id)
        profile_text = (
            "👤 <b>Yangilangan profil:</b>\n\n"
            f"📝 Ism Familiya: {updated_user.full_name}\n"
            f"📱 Telefon: {updated_user.phone}\n"
            f"🏫 Sinf: {updated_user.class_name}"
        )

        if updated_user.age is not None:
            profile_text += f"\n🎂 Yosh: {updated_user.age}"
        if updated_user.address:
            profile_text += f"\n🏠 Yashash joyi: {updated_user.address}"
        
        await message.answer(profile_text, parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        print(f"Profile update error: {e}")
        await message.answer(
            "❌ Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
        )