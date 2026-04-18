from aiogram import Router, types, F
from aiogram.types import FSInputFile
from pathlib import Path
from aiogram.filters import Command
from ..services.orm_scanner import check_answer
from aiogram.fsm.context import FSMContext
from ..states import AnswerStates
from app.config import config
import asyncio
from app.keyboards import cancel_keyboard, admin_panel_keyboard
import re


test_router = Router()


def turn_to_str(msg):
    msg = msg.lower()
    msg = re.findall(r"[a-z]", msg)
    return "".join(msg)


def _is_cancel(text: str) -> bool:
    return (text or "").strip() == "❌ Bekor qilish"


@test_router.message(F.text == "📃 ORM testlarni tekshirish")
async def start_check(msg: types.Message, state: FSMContext):
    """Testni tekshirishni boshlash"""
    if not config.is_admin(msg.from_user.id):
        await msg.answer("❌ Bu funksiya faqat adminlar uchun!")
        return

    await msg.answer(
        text="🧪 <b>TEST TEKSHIRISH REJIMI</b>\n\n"
        "Quyidagi ma'lumotlarni kiriting:\n\n"
        "1️⃣ Test raqamini kirting (son ko'rinishida):\n",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AnswerStates.waiting_test_num)


@test_router.message(AnswerStates.waiting_test_num)
async def get_test_num(msg: types.Message, state: FSMContext):
    """Test raqamini oladi"""

    if _is_cancel(msg.text):
        await state.clear()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return

    test_num = int(msg.text)

    if not test_num:
        await msg.answer("❌ Iltimos, Test raqamini kiriting")
        return
    await state.update_data(test_num=test_num)

    await msg.answer(
        f"✅ Test raqami: {test_num} kiritildi\n\n"
        "2️⃣ Matematika savollar sonini kiriting (masalan: 43)"
    )
    await state.set_state(AnswerStates.waiting_math_q_num)


@test_router.message(AnswerStates.waiting_math_q_num)
async def get_math_q_num(msg: types.Message, state: FSMContext):
    """Matematika savolar sonini oladi"""
    if _is_cancel(msg.text):
        await state.clear()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return
    try:
        math_q_num = int(msg.text.strip())
        if math_q_num <= 0:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Iltimos, to'g'ri raqam kiriting! (masalan: 43)")
        return

    await state.update_data(math_q_num=math_q_num)
    await msg.answer(
        f"✅ Matematika savollar soni qabul qilindi: {math_q_num}\n\n"
        "3️⃣ Ingliz tili savollar sonini kiriting (masalan: 20)"
    )
    await state.set_state(AnswerStates.waiting_eng_q_num)


@test_router.message(AnswerStates.waiting_eng_q_num)
async def get_eng_q_num(msg: types.Message, state: FSMContext):
    """Ingliz tili savollar sonini olida"""
    if _is_cancel(msg.text):
        await state.clear()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return
    try:
        eng_q_num = int(msg.text.strip())
        if eng_q_num <= 0:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Iltimos, to'g'ri raqam kiriting! (masalan: 20)")
        return

    await state.update_data(eng_q_num=eng_q_num)
    await msg.answer(
        f"✅ Ingliz tili savollar soni qabul qilindi: {eng_q_num}\n\n"
        "4️⃣ Matematika javoblarini kiriting (masalan: ABCDABCDABCDABCD...)\n"
        "Yoki birma-bir satr: 'a b c d a b c d...'\n"
        "Yoki raqamlar bilan: '1-a 2-b 3-c...'",
        parse_mode="HTML",
    )
    await state.set_state(AnswerStates.waiting_math_answers)


@test_router.message(AnswerStates.waiting_math_answers)
async def get_math_answers(msg: types.Message, state: FSMContext):
    """Matematika javoblarini oladi"""
    math_answers = turn_to_str(msg.text)

    if _is_cancel(msg.text):
        await state.clear()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return

    if not math_answers:
        await msg.answer("❌ Iltimos, javoblarni kiriting!")
        return
    if any(c.lower() not in "abcde" for c in math_answers):
        await msg.answer("❌ Javoblar faqat A, B, C, D, E bo'lishi kerak!")
        return
    if len(math_answers) != (await state.get_data()).get("math_q_num"):
        await msg.answer(
            f"❌ Javoblar soni matematika savollar soniga teng bo'lishi kerak! ({(await state.get_data()).get('math_q_num')})"
        )
        return

    await state.update_data(math_answers=math_answers)
    await msg.answer(
        f"✅ Matematika javoblari qabul qilindi: {math_answers[:20]}...\n\n"
        "5️⃣ Endi ingliz tili javoblarini kiriting (masalan: 1-a 2-b 3-c...)"
    )
    await state.set_state(AnswerStates.waiting_eng_answers)


@test_router.message(AnswerStates.waiting_eng_answers)
async def get_eng_answers(msg: types.Message, state: FSMContext):
    """Ingliz tili javoblarini oladi"""

    if _is_cancel(msg.text):
        await state.clear()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return

    eng_answers = turn_to_str(msg.text)
    if not eng_answers:
        await msg.answer("❌ Iltimos, javoblarni kiriting!")
        return

    if any(c.lower() not in "abcde" for c in eng_answers):
        await msg.answer("❌ Javoblar faqat A, B, C, D, E bo'lishi kerak!")
        return

    if len(eng_answers) != (await state.get_data()).get("eng_q_num"):
        await msg.answer(
            f"❌ Javoblar soni ingliz tili savollar soniga teng bo'lishi kerak! ({(await state.get_data()).get('eng_q_num')})"
        )
        return

    await state.update_data(eng_answers=eng_answers)
    await msg.answer(
        f"✅ Ingliz tili javoblari qabul qilindi: {eng_answers[:20]}...\n\n"
        "6️⃣ Endi PDF faylni jo'nating 📄"
    )
    await state.set_state(AnswerStates.waiting_pdf)


@test_router.message(AnswerStates.waiting_pdf)
async def process_pdf(msg: types.Message, state: FSMContext):
    """PDF faylni tahlil qiladi"""

    # 1. Bekor qilishni tekshirish
    if msg.text and _is_cancel(msg.text):
        await state.clear()
        # BU YERDA HAM QAVS QO'SHILDI ()
        await msg.answer(
            "❌ Jarayon bekor qilindi!", reply_markup=admin_panel_keyboard()
        )
        return

    # 2. Fayl turini tekshirish
    if not msg.document or not msg.document.file_name.lower().endswith(".pdf"):
        await msg.answer("❌ Iltimos, faqat PDF fayl jo'nating!")
        return

    try:
        data = await state.get_data()

        # 3. Faylni yuklab olish (Yaxshilangan usul)
        file = await msg.bot.get_file(msg.document.file_id)
        input_dir = Path("input")
        input_dir.mkdir(exist_ok=True)

        # Fayl nomidagi bo'sh joylarni olib tashlash (xatolik bermasligi uchun)
        safe_name = msg.document.file_name.replace(" ", "_")
        path_pdf = input_dir / safe_name

        # Yangi yuklab olish usuli
        await msg.bot.download(file, destination=path_pdf)

        status_msg = await msg.answer(
            f"📥 PDF yuklab olindi: {msg.document.file_name}\n⏳ Tahlil qilinmoqda (bu biroz vaqt olishi mumkin)..."
        )

        # 4. Skanerlash (Thread ichida)
        # Eslatma: poppler yo'li to'g'riligiga ishonch hosil qiling
        await asyncio.to_thread(
            check_answer,
            math_answers=data.get("math_answers"),
            eng_answers=data.get("eng_answers"),
            math_q_num=data.get("math_q_num"),
            eng_q_num=data.get("eng_q_num"),
            fname=str(path_pdf),
            popplerpath=r"C:\Users\user\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin",
            test_num=data.get("test_num"),
        )

        output_dir = Path("output")
        files_sent = False

        # 5. Natijalarni yuborish funksiyasi (Takrorlanishni kamaytirish uchun)
        results_map = {
            "results.pdf": "📊 Natijalar pdf",
            "eng_results.xlsx": "📊 Ingliz tili natijalari Excel",
            "math_results.xlsx": "📊 Matematika natijalari Excel",
        }

        for file_name, caption in results_map.items():
            file_path = output_dir / file_name
            if file_path.exists():
                await msg.answer_document(
                    FSInputFile(str(file_path)),
                    caption=caption,
                    reply_markup=admin_panel_keyboard(),
                )
                files_sent = True
                # Yuborilgan faylni o'chirib yuborish (ixtiyoriy, keyingi safar adashmaslik uchun)
                # os.remove(file_path)

        if not files_sent:
            await msg.answer(
                "⚠️ Tahlil tugadi, lekin natija fayllari topilmadi.",
                reply_markup=admin_panel_keyboard(),
            )

        await state.clear()

    except Exception as e:
        # Xatoni logga yozish (Terminalda ko'rinadi)
        print(f"DEBUG XATO: {e}")
        # Foydalanuvchiga xatoni yuborish (QAVS QO'SHILDI!)
        print(f"DEBUG XATO (foydalanuvchiga yuborilmoqda): {str(e)}")
        await msg.answer(
            f"❌ Tizim xatosi: {str(e)}", reply_markup=admin_panel_keyboard()
        )
        await state.clear()
