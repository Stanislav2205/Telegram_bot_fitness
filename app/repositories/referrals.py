from datetime import datetime

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, ReferralStatus


class ReferralsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_invitee_campaign(self, invitee_id: int, campaign_id: int) -> Referral | None:
        query = select(Referral).where(
            and_(
                Referral.invitee_id == invitee_id,
                Referral.campaign_id == campaign_id,
            )
        )
        return await self.session.scalar(query)

    async def create(self, inviter_id: int, invitee_id: int, campaign_id: int) -> Referral:
        referral = Referral(
            inviter_id=inviter_id,
            invitee_id=invitee_id,
            campaign_id=campaign_id,
            status=ReferralStatus.pending,
        )
        self.session.add(referral)
        await self.session.flush()
        return referral

    async def mark_verified(self, referral: Referral, now: datetime) -> None:
        referral.status = ReferralStatus.verified
        referral.verified_at = now
        await self.session.flush()

    async def pending_older_than(self, campaign_id: int, cutoff: datetime) -> list[Referral]:
        query: Select[tuple[Referral]] = select(Referral).where(
            and_(
                Referral.campaign_id == campaign_id,
                Referral.status == ReferralStatus.pending,
                Referral.created_at <= cutoff,
            )
        )
        result = await self.session.scalars(query)
        return list(result)

    async def count_by_inviter(self, inviter_id: int, status: ReferralStatus | None = None) -> int:
        conditions = [Referral.inviter_id == inviter_id]
        if status is not None:
            conditions.append(Referral.status == status)
        query = select(func.count(Referral.id)).where(and_(*conditions))
        result = await self.session.scalar(query)
        return int(result or 0)
