from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from app.db import Database
from app.keyboards import (
    admin_panel_keyboard, channels_management_keyboard,
    cancel_keyboard, main_menu_keyboard, back_button,
    tests_management_keyboard, tests_list_inline_keyboard,
    admin_user_confirm_keyboard
)
from app.states import ChannelManagement, TestCreation, ExcelExport
from app.states import TestManagement
from app.states import AdminUserCreation
from app.utils import (
    get_unique_test_code, validate_answer_key, is_valid_class
)
from app.utils import generate_excel_report
from app.config import config
import logging

router = Router(name="admin")


def _is_cancel(text: str) -> bool:
    return (text or "").strip() == "❌ Bekor qilish"


@router.message(F.text == "👨‍💼 Admin Panel")
async def admin_panel(message: Message):
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return
    
    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔙 Orqaga")
async def back_to_main(message: Message):
    is_admin_user = config.is_admin(message.from_user.id)
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(is_admin_user)
    )


@router.message(F.text == "➕ Foydalanuvchi qo'shish")
async def create_user_start(message: Message, state: FSMContext):
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return

    await message.answer(
        "📱 Yangi foydalanuvchi telefon raqamini yuboring:\n\n"
        "Masalan: +998901234567",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminUserCreation.waiting_for_phone)


@router.message(AdminUserCreation.waiting_for_phone)
async def create_user_phone(message: Message, state: FSMContext, db: Database):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    normalized_phone = db.normalize_phone(text)
    if len(normalized_phone) < 10:
        await message.answer("❌ Telefon raqam noto'g'ri. Masalan: +998901234567")
        return

    existing_user = await db.get_user_by_phone(normalized_phone)
    if existing_user:
        is_admin_user = config.is_admin(message.from_user.id)
        await message.answer(
            "⚠️ Bu telefon raqam allaqachon ro'yxatdan o'tgan foydalanuvchiga tegishli.\n"
            "Yangi foydalanuvchi yaratilmadi.\n\n"
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin_user)
        )
        await state.clear()
        return

    await state.update_data(phone=normalized_phone)
    await message.answer("👤 Ismini kiriting:")
    await state.set_state(AdminUserCreation.waiting_for_first_name)


@router.message(AdminUserCreation.waiting_for_first_name)
async def create_user_first_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    if len(text) < 2:
        await message.answer("❌ Ism juda qisqa. Qayta kiriting.")
        return

    await state.update_data(first_name=text)
    await message.answer("👤 Familiyasini kiriting:")
    await state.set_state(AdminUserCreation.waiting_for_last_name)


@router.message(AdminUserCreation.waiting_for_last_name)
async def create_user_last_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    if len(text) < 2:
        await message.answer("❌ Familiya juda qisqa. Qayta kiriting.")
        return

    await state.update_data(last_name=text)
    await message.answer("🎂 Yoshini kiriting (masalan: 16):")
    await state.set_state(AdminUserCreation.waiting_for_age)


@router.message(AdminUserCreation.waiting_for_age)
async def create_user_age(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    try:
        age = int(text)
    except ValueError:
        await message.answer("❌ Yosh uchun faqat raqam kiriting.")
        return

    if age < 5 or age > 100:
        await message.answer("❌ Yosh noto'g'ri. 5-100 oralig'ida kiriting.")
        return

    await state.update_data(age=age)
    await message.answer("🏫 Sinfini kiriting (masalan: 9-A):")
    await state.set_state(AdminUserCreation.waiting_for_class)


@router.message(AdminUserCreation.waiting_for_class)
async def create_user_class(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    if not is_valid_class(text):
        await message.answer("❌ Noto'g'ri sinf formati. Masalan: 9-A, 11-B, 10")
        return

    await state.update_data(class_name=text)
    await message.answer("🏠 Yashash joyini kiriting:")
    await state.set_state(AdminUserCreation.waiting_for_address)


@router.message(AdminUserCreation.waiting_for_address)
async def create_user_address(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if _is_cancel(text):
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    if len(text) < 3:
        await message.answer("❌ Yashash joyi juda qisqa. Qayta kiriting.")
        return

    await state.update_data(address=text)
    data = await state.get_data()

    preview = (
        "🧾 <b>Tekshirish:</b>\n\n"
        f"📱 Telefon: {data['phone']}\n"
        f"👤 Ism: {data['first_name']}\n"
        f"👤 Familiya: {data['last_name']}\n"
        f"🎂 Yosh: {data['age']}\n"
        f"🏫 Sinf: {data['class_name']}\n"
        f"🏠 Yashash joyi: {data['address']}\n\n"
        "Tasdiqlaysizmi?"
    )

    await message.answer(
        preview,
        parse_mode="HTML",
        reply_markup=admin_user_confirm_keyboard()
    )
    await state.set_state(AdminUserCreation.waiting_for_confirm)


@router.message(AdminUserCreation.waiting_for_confirm)
async def create_user_confirm(message: Message, state: FSMContext, db: Database):
    text = (message.text or "").strip()

    if text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    if text != "✅ Yaratish":
        await message.answer("Iltimos, ✅ Yaratish yoki ❌ Bekor qilish tugmasidan foydalaning.")
        return

    data = await state.get_data()
    full_name = f"{data['last_name']} {data['first_name']}"

    try:
        await db.create_pre_registered_user(
            created_by_admin_tg_id=message.from_user.id,
            full_name=full_name,
            phone=data['phone'],
            age=data['age'],
            class_name=data['class_name'],
            address=data['address']
        )
        await message.answer(
            "✅ Yangi foydalanuvchi saqlandi!\n\n"
            "Endi u /start bosib shu telefon raqamni yuborsa,"
            " avtomatik shu profilga kiradi.",
            reply_markup=admin_panel_keyboard()
        )
    except ValueError as e:
        await message.answer(f"❌ {str(e)}", reply_markup=admin_panel_keyboard())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", reply_markup=admin_panel_keyboard())
    finally:
        await state.clear()


@router.message(F.text == "📣 Kanallar")
async def channels_menu(message: Message):
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return
    
    await message.answer(
        "📣 <b>Kanallar boshqaruvi</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=channels_management_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "add_channel")
async def add_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Kanal qo'shish"""
    if not config.is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Kanal username yoki ID sini yuboring:\n\n"
        "Masalan: @mychannel yoki -1001234567890\n\n"
        "⚠️ Bot kanalda admin bo'lishi kerak!",
        parse_mode="HTML",
        reply_markup=back_button()
    )
    await state.set_state(ChannelManagement.waiting_for_channel)
    await callback.answer()


@router.message(ChannelManagement.waiting_for_channel)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot, db: Database):
    """Kanalni qo'shish"""
    channel_input = message.text.strip()
    
    if channel_input == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!")
        await state.clear()
        return
    
    try:
        if channel_input.startswith('@'):
            username = channel_input
            chat = await bot.get_chat(username)
            channel_id = chat.id
        else:
            channel_id = int(channel_input)
            chat = await bot.get_chat(channel_id)
            username = chat.username if chat.username else f"ID: {channel_id}"
        
        try:
            bot_member = await bot.get_chat_member(channel_id, bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await message.answer("❌ Bot kanalda admin emas! Iltimos, botni kanal admini qiling.")
                return
        except Exception as e:
            await message.answer(
                f"❌ Kanalni tekshirishda xatolik: {str(e)}\n"
                "Iltimos, kanal username/ID va bot huquqlarini tekshiring."
            )
            return
        
        await db.add_channel(channel_id, username)
        
        await message.answer(
            f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
            f"📢 {username}",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Username yoki ID ni to'g'ri kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


@router.callback_query(F.data == "remove_channel")
async def remove_channel_callback(callback: CallbackQuery, state: FSMContext, db: Database):
    """Kanalni o'chirish"""
    if not config.is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    channels = await db.get_all_channels()
    
    if not channels:
        await callback.answer("❌ Kanallar ro'yxati bo'sh!", show_alert=True)
        return
    
    channels_text = "➖ <b>Kanalni o'chirish</b>\n\n"
    channels_text += "Qaysi kanalni o'chirmoqchisiz?\n\n"
    
    for i, channel in enumerate(channels, 1):
        channels_text += f"{i}. {channel.username} (ID: {channel.channel_id})\n"
    
    channels_text += "\nKanal ID sini yuboring:"
    
    await callback.message.edit_text(channels_text, parse_mode="HTML", reply_markup=back_button())
    await state.set_state(ChannelManagement.waiting_for_channel_to_remove)
    await callback.answer()


@router.message(ChannelManagement.waiting_for_channel_to_remove)
async def process_remove_channel(message: Message, state: FSMContext, db: Database):
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!")
        await state.clear()
        return
    
    try:
        channel_id = int(message.text.strip())
        await db.remove_channel(channel_id)
        
        await message.answer(
            "✅ Kanal muvaffaqiyatli o'chirildi!",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


@router.callback_query(F.data == "list_channels")
async def list_channels_callback(callback: CallbackQuery, db: Database):
    if not config.is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    channels = await db.get_all_channels()
    
    if not channels:
        await callback.answer("📋 Kanallar ro'yxati bo'sh!", show_alert=True)
        return
    
    channels_text = "📋 <b>Majburiy kanallar ro'yxati:</b>\n\n"
    
    for i, channel in enumerate(channels, 1):
        channels_text += f"{i}. {channel.username}\n"
        channels_text += f"   ID: <code>{channel.channel_id}</code>\n\n"
    
    await callback.message.edit_text(
        channels_text,
        parse_mode="HTML",
        reply_markup=channels_management_keyboard()
    )
    await callback.answer()


@router.message(F.text == "🧾 Testlar")
async def tests_menu(message: Message):
    """Admin testlar boshqaruvi menyusi"""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return

    await message.answer(
        "🧾 <b>Testlar boshqaruvi</b>\n\n"
        "Quyidagi tugma orqali mavjud testlar ro'yxatini ko'ring:\n",
        reply_markup=tests_management_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📋 Testlar ro'yxati")
async def list_tests_menu(message: Message, db: Database):
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return

    tests = await db.get_all_tests()
    if not tests:
        await message.answer("📋 Hozircha testlar mavjud emas!", reply_markup=admin_panel_keyboard())
        return

    text = "📋 <b>Barcha testlar:</b>\n\n"
    for t in tests:
        text += f"• <code>{t.code}</code> — Savollar: {t.question_count}\n"

    kb = tests_list_inline_keyboard(tests)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)





@router.callback_query(lambda c: c.data and c.data.startswith("delete_test:"))
async def delete_test_callback(callback: CallbackQuery, db: Database):
    if not config.is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    code = callback.data.split(":", 1)[1]
    test = await db.get_test_by_code(code)
    if not test:
        await callback.answer("❌ Test topilmadi!", show_alert=True)
        return

    await db.remove_test(code)
    try:
        await callback.message.edit_text(f"✅ Test <code>{code}</code> muvaffaqiyatli o'chirildi!", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Test o'chirildi")


@router.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: CallbackQuery):
    is_admin_user = config.is_admin(callback.from_user.id)
    await callback.message.edit_text("👨‍💼 Admin Panel\n\nKerakli bo'limni tanlang:", reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.message(F.text == "🧪 Test yaratish")
async def create_test_start(message: Message, state: FSMContext):
    """Test yaratishni boshlash"""
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return
    
    await message.answer(
        "🧪 <b>Test yaratish</b>\n\n"
        "1️⃣ Iltimos faqat RASM(lar) yoki PDF fayl yuboring.\n\n"
        "• Bir rasm yoki bir nechta rasm (album)\n"
        "• yoki PDF fayl (butun test bitta PDFda)\n\n"
        "Bot avtomatik ravishda rasm yoki PDF ichidagi savollarni o'qiy olmaydi,\n"
        "shu uchun keyin sizdan nechta savol borligini va javob kalitini so'raydi.",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TestCreation.waiting_for_content)


@router.message(TestCreation.waiting_for_content)
async def process_test_content(message: Message, state: FSMContext):
    """Test kontentini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    file_ref = None
    file_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_ref = file_id
        file_type = "photo"
    elif message.document:
        doc = message.document
        filename = getattr(doc, 'file_name', '') or ''
        mime = getattr(doc, 'mime_type', '') or ''
        if mime == 'application/pdf' or filename.lower().endswith('.pdf'):
            file_ref = doc.file_id
            file_type = "pdf"
        else:
            await message.answer("❌ Faqat PDF fayl qabul qilinadi. Qaytadan yuboring yoki ❌ Bekor qilish.")
            return
    else:
        await message.answer("❌ Iltimos rasm yoki PDF yuboring (matn qabul qilinmaydi).")
        return

    content_value = f"{file_type}:{file_ref}"
    if message.caption:
        content_value += f"|caption:{message.caption}"

    await state.update_data(content=content_value)

    await message.answer(
        "🔢 Nechta savol bor? Iltimos faqat raqam kiriting:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(TestCreation.waiting_for_question_count)


@router.message(TestCreation.waiting_for_answer_key)
async def process_answer_key(message: Message, state: FSMContext):
    """Javob kalitini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return
    
    answer_key = message.text.strip().lower()
    
    import re
    pattern = r'(\d+)([a-d])'
    matches = re.findall(pattern, answer_key)

    data = await state.get_data()
    stored_q = data.get('question_count')
    if stored_q is not None:
        question_count = stored_q
        if len(matches) != question_count:
            await message.answer(f"❌ Javob kalitida {len(matches)} ta element topildi, lekin siz {question_count} ta savol kiritgansiz. Iltimos javob kalitini qayta tekshiring.")
            return
    else:
        question_count = len(matches)

    is_valid, error_msg = validate_answer_key(answer_key, question_count)
    
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nQaytadan kiriting:")
        return
    
    await state.update_data(
        answer_key=answer_key,
        question_count=question_count
    )
    
    await message.answer(
        f"3️⃣ <b>Ball belgilash</b>\n\n"
        f"Jami {question_count} ta savol.\n\n"
        f"Har bir to'g'ri javob uchun necha ball berilsin?\n\n"
        f"Masalan: 2",
        parse_mode="HTML"
    )
    await state.set_state(TestCreation.waiting_for_points)



@router.message(TestCreation.waiting_for_question_count)
async def process_question_count(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return

    try:
        qcount = int(message.text.strip())
        if qcount <= 0:
            await message.answer("❌ Noto'g'ri raqam. Iltimos musbat butun son kiriting.")
            return

        await state.update_data(question_count=qcount)

        await message.answer(
            "2️⃣ <b>Javob kalitini kiriting:</b>\n\n"
            "Format: 1a2b3c4a5b...\n\n"
            "Qoidalar:\n"
            "• 1 dan boshlab ketma-ket\n"
            "• Faqat a, b, c, d harflar\n\n"
            "Masalan: 1a2b3c4a5b",
            parse_mode="HTML"
        )
        await state.set_state(TestCreation.waiting_for_answer_key)

    except ValueError:
        await message.answer("❌ Iltimos faqat raqam kiriting.")


@router.message(TestCreation.waiting_for_points)
async def process_points(message: Message, state: FSMContext, bot: Bot, db: Database):
    """Ballni qabul qilish va testni yaratish"""
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return
    
    try:
        points_per_correct = float(message.text.strip())

        if points_per_correct <= 0:
            await message.answer("❌ Ball musbat son bo'lishi kerak!")
            return
        
        data = await state.get_data()
        
        logging.info("process_points: db type = %s", type(db))
        code = await get_unique_test_code(db)
        
        test_id = await db.create_test(
            code=code,
            content=data['content'],
            answer_key=data['answer_key'],
            question_count=data['question_count'],
            points_per_correct=points_per_correct
        )
        
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start={code}"
        
        max_score = data['question_count'] * points_per_correct
        
        result_text = (
            "✅ <b>Test muvaffaqiyatli yaratildi!</b>\n\n"
            f"🔢 Kod: <code>{code}</code>\n"
            f"🔗 Link: {link}\n\n"
            f"📊 Savollar soni: {data['question_count']}\n"
            f"💯 Har bir savol: {points_per_correct} ball\n"
            f"🎯 Maksimal ball: {max_score}\n\n"
            f"Test linkini yoki kodni o'quvchilarga yuboring!"
        )
        
        await message.answer(
            result_text,
            reply_markup=admin_panel_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")


@router.message(F.text == "📊 Natijalarni yuklab olish")
async def export_results_start(message: Message, state: FSMContext, db: Database):
    if not config.is_admin(message.from_user.id):
        await message.answer("❌ Bu funksiya faqat adminlar uchun!")
        return
    
    tests = await db.get_all_tests()
    
    if not tests:
        await message.answer(
            "❌ Hali testlar mavjud emas!",
            reply_markup=admin_panel_keyboard()
        )
        return
    
    tests_text = "📊 <b>Test natijalarini yuklab olish</b>\n\n"
    tests_text += "Test kodini kiriting:\n\n"
    
    for test in tests[:10]: 
        tests_text += f"• <code>{test.code}</code> - {test.question_count} ta savol\n"
    
    await message.answer(
        tests_text,
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ExcelExport.waiting_for_test_code)


@router.message(ExcelExport.waiting_for_test_code)
async def process_export_code(message: Message, state: FSMContext, db: Database):
    if message.text == "❌ Bekor qilish":
        await message.answer("❌ Bekor qilindi!", reply_markup=admin_panel_keyboard())
        await state.clear()
        return
    
    code = message.text.strip()
    
    test = await db.get_test_by_code(code)
    
    if not test:
        await message.answer("❌ Bunday test topilmadi! Qaytadan kiriting:")
        return
    
    results = await db.get_test_results_for_excel(test.id)
    
    if not results:
        await message.answer(
            "❌ Bu test uchun hali natijalar yo'q!",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
        return
    
    excel_file = await generate_excel_report(code, results)
    
    file = BufferedInputFile(
        excel_file.read(),
        filename=f"Test_{code}_natijalar.xlsx"
    )
    
    await message.answer_document(
        file,
        caption=f"📊 Test {code} natijalari\n\n"
                f"Jami ishtirokchilar: {len(results)}"
    )
    
    await message.answer(
        "✅ Excel fayl yuborildi!",
        reply_markup=admin_panel_keyboard()
    )
    await state.clear()