import asyncio
import logging
import socket
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app.handlers.admin import build_admin_router
from app.handlers.referral import build_referral_router
from app.handlers.start import build_start_router
from app.handlers.subscription import build_subscription_router
from app.jobs.draw_jobs import DrawJobs
from app.repositories.campaigns import CampaignsRepository

logging.basicConfig(level=logging.INFO)


async def on_startup() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Создаем сессию для создания кампании
    session_factory = build_session_factory(settings)
    async with session_factory() as session:
        campaign_repo = CampaignsRepository(session)
        
        # Преобразуем даты из строки в объект datetime
        start_date = datetime.strptime(settings.campaign_start_date, "%d.%m.%Y")
        end_date = datetime.strptime(settings.campaign_end_date, "%d.%m.%Y")
        
        # Проверяем, существует ли уже активная кампания с этими датами
        existing_campaigns = await campaign_repo.get_all()
        campaign_exists = any(
            c.starts_at.date() == start_date.date() and c.ends_at.date() == end_date.date()
            for c in existing_campaigns
        )
        
        if not campaign_exists:
            # Создаем новую кампанию на основе дат из конфига
            campaign = await campaign_repo.create(
                title=f"Кампания с {settings.campaign_start_date} по {settings.campaign_end_date}",
                starts_at=start_date,
                ends_at=end_date,
                top_k=1,  # по умолчанию 1 победитель
                min_days_subscribed=0
            )
            
            # Активируем кампанию
            campaign.status = "active"
            await session.commit()
            
            logging.info(f"Создана новая кампания ID: {campaign.id} - {campaign.title}")


async def main() -> None:
    await on_startup()
    settings = get_settings()
    session_factory = build_session_factory(settings)

    session = AiohttpSession(proxy=settings.telegram_proxy)
    # Force IPv4 connector to reduce intermittent WinError 121 on some networks.
    session._connector_init["family"] = socket.AF_INET
    bot = Bot(token=settings.bot_token, session=session)
    dp = Dispatcher()
    dp.include_router(build_start_router(settings, session_factory))
    dp.include_router(build_subscription_router(settings, session_factory))
    dp.include_router(build_referral_router(settings, session_factory))
    dp.include_router(build_admin_router(settings, session_factory))

    scheduler = AsyncIOScheduler(timezone=settings.draw_timezone)
    draw_jobs = DrawJobs(session_factory)
    scheduler.add_job(draw_jobs.finalize_expired_campaigns, "interval", minutes=5)
    scheduler.start()

    try:
        if settings.run_mode == "webhook":
            if not settings.webhook_base_url:
                raise ValueError("WEBHOOK_BASE_URL is required when RUN_MODE=webhook")
            if not settings.webhook_secret:
                raise ValueError("WEBHOOK_SECRET is required when RUN_MODE=webhook")

            webhook_url = f"{settings.webhook_base_url.rstrip('/')}{settings.webhook_path}"
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.webhook_secret,
                drop_pending_updates=settings.webhook_drop_pending_updates,
            )
            app = web.Application()
            webhook_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=settings.webhook_secret,
            )
            webhook_handler.register(app, path=settings.webhook_path)
            setup_application(app, dp, bot=bot)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host=settings.webhook_host, port=settings.webhook_port)
            await site.start()
            logging.info("Webhook server started at http://%s:%s%s", settings.webhook_host, settings.webhook_port, settings.webhook_path)
            logging.info("Telegram webhook set to: %s", webhook_url)
            await asyncio.Event().wait()
        else:
            await bot.delete_webhook(drop_pending_updates=False)
            retry_delay = 3
            while True:
                try:
                    await dp.start_polling(bot, polling_timeout=5)
                    break
                except (TelegramNetworkError, OSError) as exc:
                    logging.warning("Polling stopped by network issue: %s. Retry in %ss", exc, retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())