from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import CampaignStatus, Referral, ReferralStatus, Ticket
from app.repositories.audit import AuditRepository
from app.repositories.campaigns import CampaignsRepository


class CampaignService:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def create_campaign(self, title: str, starts_at: datetime, ends_at: datetime, top_k: int = 10) -> int:
        async with self.session_factory() as session:
            campaigns_repo = CampaignsRepository(session)
            campaign = await campaigns_repo.create(
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
                top_k=top_k,
                min_days_subscribed=0,
            )
            await session.commit()
            return campaign.id

    async def set_campaign_status(self, campaign_id: int, status: CampaignStatus) -> bool:
        async with self.session_factory() as session:
            campaigns_repo = CampaignsRepository(session)
            audit_repo = AuditRepository(session)
            campaign = await campaigns_repo.get_by_id(campaign_id)
            if not campaign:
                return False
            await campaigns_repo.set_status(campaign, status)
            await audit_repo.log(action="campaign.status", details=f"campaign={campaign_id},status={status.value}")
            await session.commit()
            return True

    async def get_active_campaign_id(self) -> int | None:
        async with self.session_factory() as session:
            campaigns_repo = CampaignsRepository(session)
            campaign = await campaigns_repo.get_active(datetime.now(timezone.utc))
            return campaign.id if campaign else None

    async def campaign_stats(self, campaign_id: int) -> dict[str, int]:
        async with self.session_factory() as session:
            verified_referrals = await session.scalar(
                select(func.count(Referral.id)).where(
                    Referral.campaign_id == campaign_id,
                    Referral.status == ReferralStatus.verified,
                )
            )
            total_tickets = await session.scalar(
                select(func.coalesce(func.sum(Ticket.amount), 0)).where(Ticket.campaign_id == campaign_id)
            )
            participants = await session.scalar(
                select(func.count(func.distinct(Ticket.user_id))).where(Ticket.campaign_id == campaign_id)
            )
            return {
                "verified_referrals": int(verified_referrals or 0),
                "total_tickets": int(total_tickets or 0),
                "participants": int(participants or 0),
            }
