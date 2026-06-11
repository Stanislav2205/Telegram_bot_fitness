from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Campaign, CampaignStatus
from app.services.draw_service import DrawService


class DrawJobs:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.draw_service = DrawService(session_factory)

    async def finalize_expired_campaigns(self) -> None:
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            campaigns = await session.scalars(
                select(Campaign).where(
                    Campaign.status == CampaignStatus.active,
                    Campaign.ends_at < now,
                )
            )
            for campaign in campaigns:
                try:
                    await self.draw_service.draw_for_campaign(campaign.id)
                except ValueError:
                    campaign.status = CampaignStatus.finished
            await session.commit()
