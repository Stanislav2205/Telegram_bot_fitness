from __future__ import annotations

import asyncio
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import AuditLog, Campaign, CampaignStatus, DrawResult, User
from app.texts import DRAW_START_ANNOUNCEMENT, build_draw_launch_announcement


@dataclass
class LeaderboardEntry:
    user_id: int
    telegram_id: int | None
    username: str
    confirmed_referrals: int


@dataclass
class LiveDrawOutcome:
    campaign_id: int
    winner_user_id: int
    winner_telegram_id: int | None
    winner_username: str
    winner_confirmed_referrals: int
    total_registered_participants: int
    threshold_days: int
    tie_size: int
    seed_info: str
    leaderboard: list[LeaderboardEntry]


class LiveDrawScript:
    def __init__(self, session_factory: async_sessionmaker, minimum_days: int = 0) -> None:
        self.session_factory = session_factory
        self.minimum_days = minimum_days

    async def run(self, campaign_id: int) -> LiveDrawOutcome:
        async with self.session_factory() as session:
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                raise ValueError("Кампания не найдена.")
            if campaign.status != CampaignStatus.active:
                raise ValueError("Кампания должна быть активной для запуска live-розыгрыша.")

            threshold_days = max(int(campaign.min_days_subscribed or 0), self.minimum_days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
            counts_result = await session.execute(
                select(
                    User.referred_by.label("inviter_id"),
                    func.count(User.id).label("confirmed_count"),
                )
                .where(
                    User.referred_by.is_not(None),
                    User.age.is_not(None),
                    User.favorite_sport.is_not(None),
                    User.created_at <= cutoff,
                )
                .group_by(User.referred_by)
            )
            count_rows = counts_result.all()
            if not count_rows:
                raise ValueError(
                    f"Нет участников с подтвержденными приглашениями старше {threshold_days} дней."
                )

            inviter_ids = [row.inviter_id for row in count_rows]
            users_result = await session.execute(
                select(User.id, User.username, User.telegram_id).where(User.id.in_(inviter_ids))
            )
            users_map = {
                row.id: (row.username, row.telegram_id)
                for row in users_result.all()
            }

            total_registered_participants = int(
                await session.scalar(
                    select(func.count(User.id)).where(
                        User.age.is_not(None),
                        User.favorite_sport.is_not(None),
                    )
                )
                or 0
            )

            leaderboard: list[LeaderboardEntry] = []
            for row in count_rows:
                username, telegram_id = users_map.get(row.inviter_id, (None, None))
                display_name = (
                    f"@{username}"
                    if username
                    else (f"id:{telegram_id}" if telegram_id is not None else f"user:{row.inviter_id}")
                )
                leaderboard.append(
                    LeaderboardEntry(
                        user_id=row.inviter_id,
                        telegram_id=telegram_id,
                        username=display_name,
                        confirmed_referrals=int(row.confirmed_count),
                    )
                )

            leaderboard.sort(key=lambda item: item.confirmed_referrals, reverse=True)
            max_confirmed = leaderboard[0].confirmed_referrals
            leaders = [item for item in leaderboard if item.confirmed_referrals == max_confirmed]
            winner = secrets.choice(leaders)
            seed_info = f"live-max-referrals@{datetime.now(timezone.utc).isoformat()}"

            session.add(
                DrawResult(
                    campaign_id=campaign.id,
                    winner_user_id=winner.user_id,
                    seed_info=seed_info,
                )
            )
            campaign.status = CampaignStatus.finished
            session.add(
                AuditLog(
                    action="draw.live_finished",
                    target_id=str(campaign.id),
                    details=(
                        f"winner={winner.user_id},confirmed_referrals={winner.confirmed_referrals},"
                        f"tie_size={len(leaders)},threshold_days={threshold_days}"
                    ),
                )
            )
            await session.commit()
            return LiveDrawOutcome(
                campaign_id=campaign.id,
                winner_user_id=winner.user_id,
                winner_telegram_id=winner.telegram_id,
                winner_username=winner.username,
                winner_confirmed_referrals=winner.confirmed_referrals,
                total_registered_participants=total_registered_participants,
                threshold_days=threshold_days,
                tie_size=len(leaders),
                seed_info=seed_info,
                leaderboard=leaderboard,
            )


async def animate_live_draw(bot: Bot, chat_id: int, outcome: LiveDrawOutcome) -> None:
    async def _resolve_display_name(user_id: int, fallback: str) -> str:
        try:
            user_chat = await bot.get_chat(user_id)
        except Exception:
            return fallback

        username = getattr(user_chat, "username", None)
        first_name = (getattr(user_chat, "first_name", "") or "").strip()
        last_name = (getattr(user_chat, "last_name", "") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        if full_name and username:
            return f"{full_name} (@{username})"
        if full_name:
            return full_name
        if username:
            return f"@{username}"
        return fallback

    me = await bot.get_me()
    launch_text = (
        build_draw_launch_announcement(me.username)
        if me.username
        else DRAW_START_ANNOUNCEMENT
    )
    await bot.send_message(chat_id=chat_id, text=launch_text)

    top_entries = outcome.leaderboard[:10]
    names_map = {}
    for entry in top_entries:
        target_id = entry.telegram_id if entry.telegram_id is not None else entry.user_id
        names_map[entry.user_id] = await _resolve_display_name(target_id, entry.username)

    winner_target_id = (
        outcome.winner_telegram_id
        if outcome.winner_telegram_id is not None
        else outcome.winner_user_id
    )
    winner_display_name = await _resolve_display_name(winner_target_id, outcome.winner_username)

    pool = [f"{names_map[entry.user_id]} — {entry.confirmed_referrals}" for entry in top_entries]
    if not pool:
        return

    spin_message = await bot.send_message(chat_id=chat_id, text="Подготовка розыгрыша...")
    spinner_steps = 14
    random_pool = pool.copy()
    random.shuffle(random_pool)
    for step in range(spinner_steps):
        current = random_pool[step % len(random_pool)]
        frame = (
            f"🎰 Розыгрыш... {step + 1}/{spinner_steps}\n"
            f"Кандидат: {current}\n\n"
            "Топ участников:\n"
            + "\n".join(f"- {line}" for line in pool[:5])
        )
        await spin_message.edit_text(frame)
        await asyncio.sleep(0.35)

    final_text = (
        "🏆 РЕЗУЛЬТАТ РОЗЫГРЫША\n"
        f"Победитель: {winner_display_name}\n"
        f"Подтвержденных приглашений: {outcome.winner_confirmed_referrals}\n"
        f"Всего зарегистрированных участников: {outcome.total_registered_participants}\n"
        f"Лидеров с одинаковым максимумом: {outcome.tie_size}\n\n"
        "Топ участников:\n"
        + "\n".join(f"- {line}" for line in pool[:10])
    )
    await spin_message.edit_text(final_text)
