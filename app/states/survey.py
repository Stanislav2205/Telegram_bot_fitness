from aiogram.fsm.state import State, StatesGroup


class SurveyState(StatesGroup):
    waiting_age = State()
    waiting_sport = State()
