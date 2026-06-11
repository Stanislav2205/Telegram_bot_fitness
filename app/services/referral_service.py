from __future__ import annotations

import re
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Referral, ReferralStatus, User
from app.repositories.audit import AuditRepository
from app.repositories.campaigns import CampaignsRepository
from app.repositories.referrals import ReferralsRepository
from app.repositories.tickets import TicketsRepository
from app.repositories.users import UsersRepository


@dataclass
class EnsureUserResult:
    user: User
    referral: Referral | None
    is_new: bool


class ReferralService:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    @staticmethod
    def generate_ref_code(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def normalize_payload(payload: str | None) -> str | None:
        if not payload:
            return None
        candidate = payload.strip()
        if re.fullmatch(r"[A-Za-z0-9]{6,64}", candidate):
            return candidate
        return None

    @staticmethod
    def survey_completed(user: User) -> bool:
        return user.age is not None and bool(user.favorite_sport)

    async def ensure_user(self, telegram_id: int, username: str | None, referral_code: str | None) -> EnsureUserResult:
        async with self.session_factory() as session:
            users_repo = UsersRepository(session)
            campaigns_repo = CampaignsRepository(session)
            referrals_repo = ReferralsRepository(session)
            audit_repo = AuditRepository(session)

            user = await users_repo.get_by_telegram_id(telegram_id)
            if user:
                if user.username != username:
                    await users_repo.update_username(user, username)
                await session.commit()
                return EnsureUserResult(user=user, referral=None, is_new=False)

            inviter = None
            normalized_ref_code = self.normalize_payload(referral_code)
            if normalized_ref_code:
                inviter = await users_repo.get_by_ref_code(normalized_ref_code)
                if inviter and inviter.telegram_id == telegram_id:
                    inviter = None

            created = False
            while not created:
                try:
                    user = await users_repo.create(
                        telegram_id=telegram_id,
                        username=username,
                        ref_code=self.generate_ref_code(),
                        referred_by=inviter.id if inviter else None,
                    )
                    created = True
                except IntegrityError:
                    await session.rollback()

            active_campaign = await campaigns_repo.get_active(datetime.now(timezone.utc))
            referral = None
            if active_campaign and inviter and inviter.id != user.id:
                existing = await referrals_repo.get_by_invitee_campaign(user.id, active_campaign.id)
                if not existing:
                    referral = await referrals_repo.create(inviter.id, user.id, active_campaign.id)
                    await audit_repo.log(
                        action="referral.pending",
                        details=f"invitee={user.id},inviter={inviter.id},campaign={active_campaign.id}",
                        actor_user_id=inviter.id,
                        target_id=str(user.id),
                    )
            await session.commit()
            return EnsureUserResult(user=user, referral=referral, is_new=True)

    async def save_survey(self, telegram_id: int, age: int, favorite_sport: str) -> User | None:
        async with self.session_factory() as session:
            users_repo = UsersRepository(session)
            user = await users_repo.get_by_telegram_id(telegram_id)
            if not user:
                return None
            await users_repo.save_survey(user=user, age=age, favorite_sport=favorite_sport.strip())
            await session.commit()
            return user

    async def verify_and_award(self, invitee_telegram_id: int) -> tuple[bool, str]:
        async with self.session_factory() as session:
            users_repo = UsersRepository(session)
            campaigns_repo = CampaignsRepository(session)
            referrals_repo = ReferralsRepository(session)
            tickets_repo = TicketsRepository(session)
            audit_repo = AuditRepository(session)

            user = await users_repo.get_by_telegram_id(invitee_telegram_id)
            if not user:
                return False, "Пользователь не найден. Нажмите /start ещё раз."
            if not self.survey_completed(user):
                return False, "Сначала пройдите опрос (возраст и любимый вид спорта), затем проверьте подписку."

            active_campaign = await campaigns_repo.get_active(datetime.now(timezone.utc))
            if not active_campaign:
                return False, "Не удалось завершить подтверждение участия. Попробуйте позже."

            status_messages: list[str] = []
            registration_key = f"registration:{active_campaign.id}:{user.id}"
            if not await tickets_repo.exists_by_idempotency_key(registration_key):
                await tickets_repo.create(
                    user_id=user.id,
                    campaign_id=active_campaign.id,
                    amount=1,
                    reason="registration_verified",
                    idempotency_key=registration_key,
                )
                await audit_repo.log(
                    action="participant.verified",
                    details=f"user={user.id},campaign={active_campaign.id}",
                    actor_user_id=user.id,
                    target_id=str(active_campaign.id),
                )
                status_messages.append("Участие подтверждено: вам начислен 1 билет за регистрацию и подписку.")
            else:
                status_messages.append("Ваше участие уже было подтверждено ранее.")

            referral = await referrals_repo.get_by_invitee_campaign(user.id, active_campaign.id)
            if not referral:
                return True, "\n".join(status_messages)

            if referral.status == ReferralStatus.verified:
                status_messages.append("Реферальный бонус пригласившему уже был начислен ранее.")
                return True, "\n".join(status_messages)

            referral_key = f"referral:{active_campaign.id}:{referral.id}"
            already_awarded = await tickets_repo.exists_by_idempotency_key(
                idempotency_key=referral_key
            )
            if already_awarded:
                status_messages.append("Реферальный бонус пригласившему уже был начислен ранее.")
                return True, "\n".join(status_messages)

            await referrals_repo.mark_verified(referral, datetime.now(timezone.utc))
            await tickets_repo.create(
                user_id=referral.inviter_id,
                campaign_id=active_campaign.id,
                amount=1,
                reason="referral_verified",
                idempotency_key=referral_key,
                source_referral_id=referral.id,
            )
            await audit_repo.log(
                action="referral.verified",
                details=f"referral={referral.id},invitee={referral.invitee_id},inviter={referral.inviter_id}",
                actor_user_id=referral.invitee_id,
                target_id=str(referral.id),
            )
            await session.commit()
            status_messages.append("Подписка подтверждена. Пригласившему начислен +1 билет.")
            return True, "\n".join(status_messages)
