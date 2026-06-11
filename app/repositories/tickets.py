from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket


class TicketsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        campaign_id: int,
        amount: int,
        reason: str,
        idempotency_key: str,
        source_referral_id: int | None = None,
    ) -> Ticket:
        ticket = Ticket(
            user_id=user_id,
            campaign_id=campaign_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key,
            source_referral_id=source_referral_id,
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def exists_by_source(self, campaign_id: int, source_referral_id: int, reason: str) -> bool:
        query = select(Ticket.id).where(
            Ticket.campaign_id == campaign_id,
            Ticket.source_referral_id == source_referral_id,
            Ticket.reason == reason,
        )
        return await self.session.scalar(query) is not None

    async def exists_by_idempotency_key(self, idempotency_key: str) -> bool:
        query = select(Ticket.id).where(Ticket.idempotency_key == idempotency_key)
        return await self.session.scalar(query) is not None

    async def get_total_by_user(self, user_id: int, campaign_id: int) -> int:
        query = select(func.coalesce(func.sum(Ticket.amount), 0)).where(
            Ticket.user_id == user_id,
            Ticket.campaign_id == campaign_id,
        )
        total = await self.session.scalar(query)
        return int(total or 0)
