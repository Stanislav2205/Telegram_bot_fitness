from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.keyboards import main_menu_keyboard
from app.repositories.users import UsersRepository
from app.services.anti_fraud_service import AntiFraudService
from app.services.campaign_service import CampaignService
from app.services.referral_service import ReferralService
from app.services.subscription_service import SubscriptionService
from app.states.survey import SurveyState


def build_subscription_router(settings: Settings, session_factory: async_sessionmaker) -> Router:
    router = Router(name="subscription")
    referral_service = ReferralService(session_factory)
    campaign_service = CampaignService(session_factory)
    anti_fraud = AntiFraudService(max_events=4, window_seconds=20)

    @router.callback_query(F.data == "check_subscription")
    async def check_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
        if anti_fraud.is_limited(callback.from_user.id):
            await callback.message.answer("Слишком часто проверяете подписку. Попробуйте через 20 секунд.")
            await callback.answer()
            return
        subscription_service = SubscriptionService(callback.bot, settings.channel_id)
        is_subscribed = await subscription_service.is_subscribed(callback.from_user.id)
        if not is_subscribed:
            await callback.message.answer(
                "Пока не вижу подписку на канал. Подпишитесь и нажмите кнопку снова."
            )
            await callback.answer()
            return

        async with session_factory() as session:
            users_repo = UsersRepository(session)
            user = await users_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.message.answer("Сначала нажмите /start.")
            await callback.answer()
            return

        if not referral_service.survey_completed(user):
            await state.set_state(SurveyState.waiting_age)
            await callback.message.answer(
                "Подписка подтверждена.\n"
                "Шаг 2: введите ваш возраст числом (например, 27)."
            )
            await callback.answer()
            return

        campaign_id = await campaign_service.get_active_campaign_id()
        if campaign_id:
            success, message = await referral_service.verify_and_award(callback.from_user.id)
            await callback.message.answer(message)
        else:
            success = False
        ref_link = f"https://t.me/{settings.bot_username}?start={user.ref_code}"
        follow_up = (
            "Доступ к разделам открыт.\n\n"
            f"Ваша персональная ссылка:\n{ref_link}"
        )
        if not success:
            follow_up = (
                "Вы уже можете приглашать друзей по вашей ссылке:\n"
                f"{ref_link}\n\n"
                "Разделы «Моя ссылка», «Мой прогресс» и «Правила» уже доступны."
            )
        await callback.message.answer(
            follow_up,
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()

    return router
