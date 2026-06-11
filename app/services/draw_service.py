from __future__ import annotations

import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import CampaignStatus, DrawResult, Ticket
from app.repositories.audit import AuditRepository
from app.repositories.campaigns import CampaignsRepository


@dataclass
class DrawOutcome:
    winner_user_ids: list[int]
    seed_info: str


class DrawService:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def draw_for_campaign(self, campaign_id: int, winners_count: int = 1) -> DrawOutcome:
        async with self.session_factory() as session:
            campaigns_repo = CampaignsRepository(session)
            audit_repo = AuditRepository(session)
            campaign = await campaigns_repo.get_by_id(campaign_id)
            if not campaign:
                raise ValueError("Campaign not found")

            ticket_rows = await session.scalars(
                select(Ticket).where(
                    and_(
                        Ticket.campaign_id == campaign.id,
                        Ticket.amount > 0,
                    )
                )
            )
            buckets = defaultdict(int)
            for row in ticket_rows:
                buckets[row.user_id] += row.amount

            population: list[int] = []
            for user_id, amount in buckets.items():
                population.extend([user_id] * amount)

            if not population:
                raise ValueError("No eligible tickets")

            selected: list[int] = []
            while len(selected) < winners_count and population:
                winner = secrets.choice(population)
                selected.append(winner)
                population = [user_id for user_id in population if user_id != winner]

            seed_info = f"secrets.choice@{datetime.now(timezone.utc).isoformat()}"
            for winner_id in selected:
                session.add(DrawResult(campaign_id=campaign.id, winner_user_id=winner_id, seed_info=seed_info))

            campaign.status = CampaignStatus.finished
            await audit_repo.log(
                action="draw.finished",
                details=f"campaign={campaign.id},winners={selected}",
                target_id=str(campaign.id),
            )
            await session.commit()
            return DrawOutcome(winner_user_ids=selected, seed_info=seed_info)
