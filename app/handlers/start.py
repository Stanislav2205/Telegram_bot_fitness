from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.keyboards import main_menu_keyboard, subscription_keyboard
from app.repositories.tickets import TicketsRepository
from app.services.anti_fraud_service import AntiFraudService
from app.services.campaign_service import CampaignService
from app.services.referral_service import ReferralService
from app.states.survey import SurveyState


def build_start_router(settings: Settings, session_factory: async_sessionmaker) -> Router:
    router = Router(name="start")
    referral_service = ReferralService(session_factory)
    campaign_service = CampaignService(session_factory)
    anti_fraud = AntiFraudService(max_events=6, window_seconds=30)

    def _build_onboarding_text() -> str:
        return (
            "Добро пожаловать в реферальный розыгрыш.\n\n"
            "Шаг 1: подпишитесь на канал и нажмите «Проверить подписку».\n"
            "После подтверждения подписки бот задаст 2 вопроса:\n"
            "- Ваш возраст\n"
            "- Каким видом спорта вы увлекаетесь"
        )

    async def _resolve_channel_link(bot) -> str | None:
        if settings.channel_link:
            return settings.channel_link
        try:
            return await bot.export_chat_invite_link(settings.channel_id)
        except TelegramAPIError:
            return None

    async def _needs_subscription_flow(user) -> bool:
        if not referral_service.survey_completed(user):
            return True
        campaign_id = await campaign_service.get_active_campaign_id()
        if not campaign_id:
            return False
        async with session_factory() as session:
            tickets_repo = TicketsRepository(session)
            registration_key = f"registration:{campaign_id}:{user.id}"
            return not await tickets_repo.exists_by_idempotency_key(registration_key)

    @router.message(CommandStart())
    async def start_handler(message: Message, command: CommandObject, state: FSMContext) -> None:
        if anti_fraud.is_limited(message.from_user.id):
            await message.answer("Слишком много запросов. Повторите через несколько секунд.")
            return
        await state.clear()
        payload = command.args if command and command.args else None
        result = await referral_service.ensure_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            referral_code=payload,
        )

        ref_link = f"https://t.me/{settings.bot_username}?start={result.user.ref_code}"
        if not result.is_new:
            if await _needs_subscription_flow(result.user):
                channel_link = await _resolve_channel_link(message.bot)
                text = _build_onboarding_text()
                if not channel_link:
                    text += "\n\nНе удалось получить ссылку на канал. Обратитесь к администратору."
                await message.answer(text, reply_markup=subscription_keyboard(channel_link=channel_link))
                return
            await message.answer(
                "Вы уже зарегистрированы.\n\n"
                f"Ваша персональная ссылка:\n{ref_link}\n\n"
                "Используйте разделы «Моя ссылка», «Мой прогресс» и «Правила».",
                reply_markup=main_menu_keyboard(),
            )
            return

        channel_link = await _resolve_channel_link(message.bot)
        text = _build_onboarding_text()
        if not channel_link:
            text += "\n\nНе удалось получить ссылку на канал. Обратитесь к администратору."
        await message.answer(
            text,
            reply_markup=subscription_keyboard(channel_link=channel_link),
        )

    @router.message(SurveyState.waiting_age)
    async def survey_age_handler(message: Message, state: FSMContext) -> None:
        age_text = (message.text or "").strip()
        if not age_text.isdigit():
            await message.answer("Возраст должен быть числом. Введите, пожалуйста, например: 27")
            return
        age = int(age_text)
        if age < 10 or age > 100:
            await message.answer("Укажите возраст в диапазоне от 10 до 100.")
            return
        await state.update_data(age=age)
        await state.set_state(SurveyState.waiting_sport)
        await message.answer("Спасибо! Теперь напишите, каким спортом вы увлекаетесь.")

    @router.message(SurveyState.waiting_sport)
    async def survey_sport_handler(message: Message, state: FSMContext) -> None:
        sport = (message.text or "").strip()
        if len(sport) < 2:
            await message.answer("Ответ слишком короткий. Напишите вид спорта словами.")
            return
        data = await state.get_data()
        age = int(data["age"])
        user = await referral_service.save_survey(
            telegram_id=message.from_user.id,
            age=age,
            favorite_sport=sport,
        )
        await state.clear()
        if not user:
            await message.answer("Не удалось сохранить анкету. Нажмите /start и повторите.")
            return
        campaign_id = await campaign_service.get_active_campaign_id()
        if campaign_id:
            success, verify_message = await referral_service.verify_and_award(message.from_user.id)
            await message.answer(verify_message)
        else:
            success = False
        ref_link = f"https://t.me/{settings.bot_username}?start={user.ref_code}"
        final_text = (
            "Готово! Регистрация завершена.\n\n"
            f"Ваша персональная ссылка, отправьте её друзьям, чтобы они смогли подписаться на канал:\n{ref_link}\n\n"
            "Теперь доступны разделы «Моя ссылка», «Мой прогресс» и «Правила»."
        )
        if not success:
            final_text = (
                "Анкета сохранена. Вы уже можете делиться ссылкой для друзей:\n"
                f"{ref_link}\n\n"
                "Разделы «Моя ссылка», «Мой прогресс» и «Правила» уже доступны."
            )
        await message.answer(final_text, reply_markup=main_menu_keyboard())

    @router.callback_query(F.data == "rules")
    async def rules_handler(callback: CallbackQuery) -> None:
        await callback.message.answer(
            "Правила:\n"
            "- Участвуют и старые, и новые подписчики.\n"
            "- Обязательна регистрация через бота.\n"
            "- Обязателен опрос (возраст и любимый спорт).\n"
            "- Один друг засчитывается один раз.\n"
            "- Самоприглашения не учитываются.\n"
            "- Реферал учитывается только после подтвержденной подписки."
        )
        await callback.answer()

    return router
