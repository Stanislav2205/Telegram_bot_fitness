from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.db.models import CampaignStatus
from app.scripts.live_draw import LiveDrawScript, animate_live_draw
from app.services.campaign_service import CampaignService
from app.services.draw_service import DrawService


def build_admin_router(settings: Settings, session_factory: async_sessionmaker) -> Router:
    router = Router(name="admin")
    campaign_service = CampaignService(session_factory)
    draw_service = DrawService(session_factory)
    live_draw_script = LiveDrawScript(session_factory)

    def _is_admin(user_id: int) -> bool:
        return user_id in settings.admin_ids

    @router.message(Command("campaign_new"))
    async def campaign_new_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        # format: /campaign_new SummerCup|2026-05-10T12:00:00|2026-05-20T12:00:00|10
        payload = message.text.removeprefix("/campaign_new").strip()
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) < 4:
            await message.answer("Формат: /campaign_new title|starts_at_iso|ends_at_iso|top_k")
            return
        title, starts_raw, ends_raw, top_k_raw = parts[:4]
        starts_at = datetime.fromisoformat(starts_raw).astimezone(timezone.utc)
        ends_at = datetime.fromisoformat(ends_raw).astimezone(timezone.utc)
        campaign_id = await campaign_service.create_campaign(title, starts_at, ends_at, top_k=int(top_k_raw))
        await message.answer(f"Кампания создана: id={campaign_id}")

    @router.message(Command("campaign_start"))
    async def campaign_start_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Формат: /campaign_start <campaign_id>")
            return
        ok = await campaign_service.set_campaign_status(int(parts[1]), CampaignStatus.active)
        await message.answer("Кампания активирована." if ok else "Кампания не найдена.")

    @router.message(Command("campaign_stop"))
    async def campaign_stop_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Формат: /campaign_stop <campaign_id>")
            return
        ok = await campaign_service.set_campaign_status(int(parts[1]), CampaignStatus.finished)
        await message.answer("Кампания завершена." if ok else "Кампания не найдена.")

    @router.message(Command("campaign_stats"))
    async def campaign_stats_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Формат: /campaign_stats <campaign_id>")
            return
        stats = await campaign_service.campaign_stats(int(parts[1]))
        await message.answer(
            f"Статистика кампании {parts[1]}:\n"
            f"- verified_referrals: {stats['verified_referrals']}\n"
            f"- total_tickets: {stats['total_tickets']}\n"
            f"- participants: {stats['participants']}"
        )

    @router.message(Command("draw"))
    async def draw_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Формат: /draw <campaign_id> [winners_count]")
            return
        winners_count = 1
        if len(parts) == 3 and parts[2].isdigit():
            winners_count = int(parts[2])
        try:
            outcome = await draw_service.draw_for_campaign(int(parts[1]), winners_count=winners_count)
        except ValueError as exc:
            await message.answer(f"Ошибка розыгрыша: {exc}")
            return
        await message.answer(
            f"Розыгрыш завершен.\nПобедители (user_id): {', '.join(map(str, outcome.winner_user_ids))}\n"
            f"Источник случайности: {outcome.seed_info}"
        )

    @router.message(Command("draw_live"))
    async def draw_live_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("Формат: /draw_live <campaign_id>")
            return
        campaign_id = int(parts[1])
        try:
            outcome = await live_draw_script.run(campaign_id)
        except ValueError as exc:
            await message.answer(f"Ошибка live-розыгрыша: {exc}")
            return

        await animate_live_draw(message.bot, settings.channel_id, outcome)
        await message.answer(
            "Live-розыгрыш завершен.\n"
            f"Победитель: {outcome.winner_username}\n"
            f"Подтвержденных приглашений: {outcome.winner_confirmed_referrals}"
        )

    @router.message(Command("export"))
    async def export_handler(message: Message) -> None:
        if not _is_admin(message.from_user.id):
            return
        await message.answer("Экспорт можно подключить через CSV выгрузку из SQL запроса по таблицам referrals/tickets.")

    return router
