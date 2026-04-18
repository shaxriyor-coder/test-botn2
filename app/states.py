from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.state import StatesGroup, State

class AdminPromotion(StatesGroup):
    waiting_for_id = State()

class Registration(StatesGroup):
    waiting_for_contact = State()
    waiting_for_name = State()
    waiting_for_class = State()


class ProfileEdit(StatesGroup):
    waiting_for_name = State()
    waiting_for_class = State()


class ChannelManagement(StatesGroup):
    waiting_for_channel = State()
    waiting_for_channel_to_remove = State()


class TestCreation(StatesGroup):
    waiting_for_content = State()
    waiting_for_question_count = State()
    waiting_for_answer_key = State()
    waiting_for_points = State()


class TestManagement(StatesGroup):
    waiting_for_test_to_remove = State()


class TestSolving(StatesGroup):
    waiting_for_answer = State()


class TestCodeInput(StatesGroup):
    waiting_for_code = State()


class RankCodeSearch(StatesGroup):
    waiting_for_code = State()


class ExcelExport(StatesGroup):
    waiting_for_test_code = State()


class AdminUserCreation(StatesGroup):
    waiting_for_phone = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_age = State()
    waiting_for_class = State()
    waiting_for_address = State()
    waiting_for_confirm = State()


class AdminPromotion(StatesGroup):
    waiting_for_username = State()
    waiting_for_id = State()
