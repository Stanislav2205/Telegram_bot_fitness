from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.repositories.campaigns import CampaignsRepository
from app.repositories.tickets import TicketsRepository
from app.repositories.users import UsersRepository


def build_referral_router(settings: Settings, session_factory: async_sessionmaker) -> Router:
    router = Router(name="referral")

    @router.callback_query(F.data == "my_ref_link")
    async def my_ref_link_handler(callback: CallbackQuery) -> None:
        async with session_factory() as session:
            users_repo = UsersRepository(session)
            user = await users_repo.get_by_telegram_id(callback.from_user.id)
            if not user:
                await callback.message.answer("Сначала выполните /start.")
                await callback.answer()
                return
            link = f"https://t.me/{settings.bot_username}?start={user.ref_code}"
            await callback.message.answer(
                "Ваша ссылка для приглашения друзей в бота:\n"
                f"{link}\n\n"
                "Отправьте именно эту ссылку. Друг должен перейти в бота и пройти регистрацию.\n"
                "Не отправляйте ссылку на канал — она другая."
            )
        await callback.answer()

    @router.callback_query(F.data == "my_progress")
    async def my_progress_handler(callback: CallbackQuery) -> None:
        async with session_factory() as session:
            users_repo = UsersRepository(session)
            campaigns_repo = CampaignsRepository(session)
            tickets_repo = TicketsRepository(session)
            user = await users_repo.get_by_telegram_id(callback.from_user.id)
            if not user:
                await callback.message.answer("Сначала выполните /start.")
                await callback.answer()
                return
            invited_total = await users_repo.count_referred(user.id)
            subscribed_total = await users_repo.count_referred_with_survey(user.id)
            from datetime import datetime, timezone

            campaign = await campaigns_repo.get_active(datetime.now(timezone.utc))
            if not campaign:
                await callback.message.answer(
                    "Ваш прогресс:\n"
                    f"- Приглашено друзей: {invited_total}\n"
                    f"- Подтверждено подписок: {subscribed_total}\n"
                    "- Билеты: 0"
                )
                await callback.answer()
                return
            total = await tickets_repo.get_total_by_user(user.id, campaign.id)
            await callback.message.answer(
                f"Ваш прогресс в кампании «{campaign.title}»:\n"
                f"- Приглашено друзей: {invited_total}\n"
                f"- Подтверждено подписок: {subscribed_total}\n"
                f"- Билетов: {total}\n"
                "- Чем больше билетов, тем выше шанс выиграть."
            )
        await callback.answer()

    return router
