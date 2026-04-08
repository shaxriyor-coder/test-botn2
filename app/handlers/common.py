from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.db import Database
from app.config import config
from app.keyboards import main_menu_keyboard, subscription_check_keyboard, profile_keyboard
from app.keyboards import rank_options_keyboard, only_back_reply_keyboard
from app.utils import check_user_subscription, validate_user_answer, check_answers
from app.states import Registration, TestSolving
from app.keyboards import back_button
from aiogram.types import CallbackQuery
from app.states import TestCodeInput, RankCodeSearch

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot, db: Database):
    user_id = message.from_user.id
    
    args = message.text.split()
    if len(args) > 1:
        test_code = args[1]
        await state.update_data(pending_test_code=test_code)
    
    is_subscribed, unsubscribed = await check_user_subscription(bot, user_id, db)
    
    if not is_subscribed:
        if unsubscribed:
            await message.answer(
                "🔔 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=subscription_check_keyboard(unsubscribed)
            )
            return
    
    user = await db.get_user(user_id)
    if not user or not user.is_profile_complete:
        from app.handlers.registration import start_registration
        await start_registration(message, state, include_back=False)
        return
    
    is_admin = config.is_admin(user_id)
    
    data = await state.get_data()
    if 'pending_test_code' in data:
        test_code = data['pending_test_code']
        test = await db.get_test_by_code(test_code)
        
        if test:
            existing_result = await db.get_user_result(test.id, user.id)
            
            if existing_result:
                rank = await db.get_user_rank(test.id, user.id)
                
                def fmt(x):
                    if isinstance(x, float) and x.is_integer():
                        return str(int(x))
                    return str(round(x, 2))
                
                await message.answer(
                    f"ℹ️ <b>Siz bu testni allaqachon ishlagansiz!</b>\n\n"
                    f"📊 Test: <code>{test_code}</code>\n"
                    f"✔️ To'g'ri: {existing_result.correct}\n"
                    f"❌ Noto'g'ri: {existing_result.wrong}\n"
                    f"💯 Ball: {fmt(existing_result.score)}/{fmt(test.max_score)}\n"
                    f"🏆 O'riningiz: {rank}\n\n"
                    f"⚠️ Bir testni faqat bir marta ishlash mumkin!",
                    parse_mode="HTML"
                )
                await state.clear()
                await message.answer(
                    "Asosiy menyu:",
                    reply_markup=main_menu_keyboard(is_admin)
                )
                return
            
            await message.answer(
                f"📝 Test kodi: {test_code}\n"
                f"📊 Savollar soni: {test.question_count}\n"
                f"💯 Har bir to'g'ri javob: {test.points_per_correct} ball\n\n"
                f"Test savollarini quyida ko'rasiz 👇"
            )
            from app.utils import send_test_content
            await send_test_content(message, test.content)
            await message.answer(
                f"✍️ Javoblarni quyidagi formatda yuboring:\n\n"
                f"Masalan: 1a2b3c4a5b...\n\n"
                f"⚠️ Barcha {test.question_count} ta savolga javob bering!"
            )
            await state.update_data(
                active_test_id=test.id, 
                active_test_code=test_code, 
                pending_test_code=None
            )
            await state.set_state(TestSolving.waiting_for_answer)
        else:
            await state.clear()
    else:
        await message.answer(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin)
        )


@router.message(F.text == "📝 Test topshirish")
async def start_test_submission(message: Message, state: FSMContext):
    await message.answer("🔢 Iltimos test kodini yuboring:", reply_markup=only_back_reply_keyboard())
    await state.set_state(TestCodeInput.waiting_for_code)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    callback: CallbackQuery, 
    state: FSMContext, 
    bot: Bot, 
    db: Database
):
    user_id = callback.from_user.id
    
    is_subscribed, _ = await check_user_subscription(bot, user_id, db)
    
    if not is_subscribed:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!",
            show_alert=True
        )
        return
    
    await callback.answer("✅ Obuna tasdiqlandi!", show_alert=True)
    await callback.message.delete()
    
    user = await db.get_user(user_id)
    if not user or not user.is_profile_complete:
        from app.handlers.registration import start_registration
        await start_registration(callback.message, state, include_back=False)
    else:
        is_admin = config.is_admin(user_id)
        
        data = await state.get_data()
        if 'pending_test_code' in data:
            test_code = data['pending_test_code']
            test = await db.get_test_by_code(test_code)
            
            if test:
                existing_result = await db.get_user_result(test.id, user.id)
                
                if existing_result:
                    rank = await db.get_user_rank(test.id, user.id)
                    
                    def fmt(x):
                        if isinstance(x, float) and x.is_integer():
                            return str(int(x))
                        return str(round(x, 2))
                    
                    await callback.message.answer(
                        f"ℹ️ <b>Siz bu testni allaqachon ishlagansiz!</b>\n\n"
                        f"📊 Test: <code>{test_code}</code>\n"
                        f"✔️ To'g'ri: {existing_result.correct}\n"
                        f"❌ Noto'g'ri: {existing_result.wrong}\n"
                        f"💯 Ball: {fmt(existing_result.score)}/{fmt(test.max_score)}\n"
                        f"🏆 O'riningiz: {rank}\n\n"
                        f"⚠️ Bir testni faqat bir marta ishlash mumkin!",
                        parse_mode="HTML"
                    )
                    await state.clear()
                    await callback.message.answer(
                        "Asosiy menyu:",
                        reply_markup=main_menu_keyboard(is_admin)
                    )
                    return
                
                await callback.message.answer(
                    f"📝 Test kodi: {test_code}\n"
                    f"📊 Savollar soni: {test.question_count}\n\n"
                    f"Test savollarini quyida ko'rasiz 👇"
                )
                from app.utils import send_test_content
                await send_test_content(callback.message, test.content)
                await callback.message.answer(
                    f"✍️ Javoblarni formatda yuboring: 1a2b3c...\n"
                    f"⚠️ Barcha {test.question_count} ta savolga javob bering!"
                )
                await state.update_data(
                    active_test_id=test.id,
                    active_test_code=test_code,
                    pending_test_code=None
                )
                await state.set_state(TestSolving.waiting_for_answer)
            else:
                await state.clear()
        else:
            await callback.message.answer(
                "Asosiy menyu:",
                reply_markup=main_menu_keyboard(is_admin)
            )


@router.message(F.text == "👤 Profil")
async def show_profile(message: Message, bot: Bot, db: Database):
    user_id = message.from_user.id
    
    is_subscribed, unsubscribed = await check_user_subscription(bot, user_id, db)
    if not is_subscribed:
        if unsubscribed:
            await message.answer(
                "🔔 Botdan foydalanish uchun kanallarga obuna bo'ling:",
                reply_markup=subscription_check_keyboard(unsubscribed)
            )
        return
    
    user = await db.get_user(user_id)
    
    if not user or not user.is_profile_complete:
        await message.answer("❌ Profil topilmadi! /start ni yuboring.")
        return
    
    profile_text = (
        "👤 <b>Sizning profilingiz:</b>\n\n"
        f"📝 Ism Familiya: {user.full_name}\n"
        f"📱 Telefon: {user.phone}\n"
        f"🏫 Sinf: {user.class_name}"
    )

    if user.age is not None:
        profile_text += f"\n🎂 Yosh: {user.age}"
    if user.address:
        profile_text += f"\n🏠 Yashash joyi: {user.address}"
    
    await message.answer(
        profile_text, 
        reply_markup=profile_keyboard(), 
        parse_mode="HTML"
    )


@router.message(F.text == "🏆 O'rnimni ko'rish")
async def rank_menu(message: Message):
    await message.answer(
        "🏆 O'rinlarni ko'rish uchun usulni tanlang:",
        reply_markup=rank_options_keyboard()
    )


@router.message(F.text == "🔢 Kod kiritish")
async def enter_test_code(message: Message, state: FSMContext):
    await message.answer("🔢 Iltimos test kodini yuboring:", reply_markup=only_back_reply_keyboard())
    await state.set_state(TestCodeInput.waiting_for_code)


@router.callback_query(F.data == "my_tests")
async def my_tests_callback(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Profil topilmadi, /start yuboring.", show_alert=True)
        return

    tests = await db.get_user_tests(user.id)
    if not tests:
        await callback.message.answer("Siz hali testlardan qatnashmagansiz.")
        await callback.answer()
        return

    text = "📋 <b>Siz qatnashgan testlar:</b>\n\n"
    for row in tests:
        finished = row.get('finished_at')
        text += (f"• <code>{row.get('code')}</code> — Ball: {row.get('score')} — "
                 f"To'g'ri: {row.get('correct')} — Noto'g'ri: {row.get('wrong')} — "
                 f"{finished}\n")

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "search_by_code")
async def search_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RankCodeSearch.waiting_for_code)
    await callback.message.answer(
        "🔎 Test kodini kiriting:",
        reply_markup=only_back_reply_keyboard()
    )
    await callback.answer()


@router.message(TestCodeInput.waiting_for_code)
async def input_test_code(message: Message, state: FSMContext, db: Database, bot: Bot):
    code = message.text.strip()
    test = await db.get_test_by_code(code)
    if not test:
        await message.answer("❌ Bunday test topilmadi. Qaytadan kiriting yoki 🔙 Orqaga.")
        return

    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi. /start ni yuboring.")
        await state.clear()
        return
    
    existing_result = await db.get_user_result(test.id, user.id)
    
    if existing_result:
        rank = await db.get_user_rank(test.id, user.id)
        
        def fmt(x):
            if isinstance(x, float) and x.is_integer():
                return str(int(x))
            return str(round(x, 2))
        
        await message.answer(
            f"ℹ️ <b>Siz bu testni allaqachon ishlagansiz!</b>\n\n"
            f"📊 Test: <code>{code}</code>\n"
            f"✔️ To'g'ri: {existing_result.correct}\n"
            f"❌ Noto'g'ri: {existing_result.wrong}\n"
            f"💯 Ball: {fmt(existing_result.score)}/{fmt(test.max_score)}\n"
            f"🏆 O'riningiz: {rank}\n\n"
            f"⚠️ Bir testni faqat bir marta ishlash mumkin!",
            parse_mode="HTML"
        )
        await state.clear()
        is_admin = config.is_admin(message.from_user.id)
        await message.answer(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin)
        )
        return

    await message.answer(
        f"📝 Test kodi: {code}\n📊 Savollar soni: {test.question_count}\n\nTest savollarini quyida ko'rasiz 👇"
    )
    from app.utils import send_test_content
    await send_test_content(message, test.content)
    await message.answer(
        f"✍️ Javoblarni quyidagi formatda yuboring:\nMasalan: 1a2b3c...\n⚠️ Barcha {test.question_count} ta savolga javob bering!"
    )
    await state.update_data(active_test_id=test.id, active_test_code=code)
    await state.set_state(TestSolving.waiting_for_answer)


@router.message(RankCodeSearch.waiting_for_code)
async def rank_code_input(message: Message, state: FSMContext, db: Database):
    code = message.text.strip()
    test = await db.get_test_by_code(code)
    if not test:
        await message.answer("❌ Bunday test topilmadi. Qaytadan kiriting yoki 🔙 Orqaga.")
        return

    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi. /start ni yuboring.")
        await state.clear()
        return

    result = await db.get_user_result(test.id, user.id)
    if not result:
        await message.answer("Siz bu testda qatnashmagansiz.")
        await state.clear()
        return

    rank = await db.get_user_rank(test.id, user.id)
    
    def fmt(x):
        if isinstance(x, float) and x.is_integer():
            return str(int(x))
        return str(round(x, 2))
    
    await message.answer(
        f"📊 Test: {code}\n🏆 O'rningiz: {rank}\n💯 Ball: {fmt(result.score)}\n✔️ To'g'ri: {result.correct}\n❌ Noto'g'ri: {result.wrong}"
    )
    await state.clear()


@router.message(TestSolving.waiting_for_answer)
async def process_test_answer(message: Message, state: FSMContext, db: Database):
    user_answer = message.text.strip()
    
    data = await state.get_data()
    test_id = data.get('active_test_id')
    test_code = data.get('active_test_code')
    
    if not test_id or not test_code:
        await message.answer("❌ Test ma'lumoti topilmadi. /start yuboring.")
        await state.clear()
        return
    
    test = await db.get_test_by_code(test_code)
    if not test:
        await message.answer("❌ Test topilmadi.")
        await state.clear()
        return
    
    is_valid, error_msg = validate_user_answer(user_answer, test.question_count)
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nQaytadan yuboring yoki 👇 /start")
        return
    
    correct_count, wrong_count = check_answers(user_answer, test.answer_key)
    score = correct_count * test.points_per_correct
    
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi.")
        await state.clear()
        return
    
    await db.save_test_result(test_id, user.id, correct_count, wrong_count, score)
    
    rank = await db.get_user_rank(test.id, user.id)
    
    def fmt(x):
        if isinstance(x, float) and x.is_integer():
            return str(int(x))
        return str(round(x, 2))

    result_text = (
        f"✅ <b>Javob qabul qilindi!</b>\n\n"
        f"📊 Test: <code>{test_code}</code>\n"
        f"✔️ To'g'ri: {correct_count}\n"
        f"❌ Noto'g'ri: {wrong_count}\n"
        f"💯 Ball: {fmt(score)}/{fmt(test.max_score)}\n"
        f"🏆 Sizning o'riningiz: {rank}"
    )
    
    await message.answer(result_text, parse_mode="HTML")
    
    is_admin = config.is_admin(message.from_user.id)
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(is_admin)
    )
    await state.clear()


@router.callback_query(F.data == "back")
async def inline_back_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.clear()
    is_admin = config.is_admin(user_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard(is_admin))
    await callback.answer()


@router.message(F.text == "🔙 Orqaga")
async def back_to_main(message: Message, state: FSMContext, bot: Bot, db: Database):
    user_id = message.from_user.id

    is_subscribed, unsubscribed = await check_user_subscription(bot, user_id, db)
    if not is_subscribed:
        if unsubscribed:
            await message.answer(
                "🔔 Botdan foydalanish uchun kanallarga obuna bo'ling:",
                reply_markup=subscription_check_keyboard(unsubscribed)
            )
        return

    user = await db.get_user(user_id)
    if not user or not user.is_profile_complete:
        from app.handlers.registration import start_registration
        await start_registration(message, state, include_back=True)
        return

    is_admin = config.is_admin(user_id)
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(is_admin)
    )