from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign, CampaignStatus


class CampaignsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self, now: datetime) -> Campaign | None:
        _ = now
        query = (
            select(Campaign)
            .where(Campaign.status == CampaignStatus.active)
            .order_by(Campaign.id.desc())
            .limit(1)
        )
        return await self.session.scalar(query)

    async def get_by_id(self, campaign_id: int) -> Campaign | None:
        return await self.session.get(Campaign, campaign_id)

    async def get_all(self) -> list[Campaign]:
        query = select(Campaign).order_by(Campaign.id.desc())
        result = await self.session.scalars(query)
        return result.all()

    async def create(self, title: str, starts_at: datetime, ends_at: datetime, top_k: int, min_days_subscribed: int) -> Campaign:
        campaign = Campaign(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            top_k=top_k,
            min_days_subscribed=min_days_subscribed,
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def set_status(self, campaign: Campaign, status: CampaignStatus) -> None:
        campaign.status = status
        await self.session.flush()