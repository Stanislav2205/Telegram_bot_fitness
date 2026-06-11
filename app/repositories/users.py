from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UsersRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        query = select(User).where(User.telegram_id == telegram_id)
        return await self.session.scalar(query)

    async def get_by_ref_code(self, ref_code: str) -> User | None:
        query = select(User).where(User.ref_code == ref_code)
        return await self.session.scalar(query)

    async def create(self, telegram_id: int, username: str | None, ref_code: str, referred_by: int | None) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            ref_code=ref_code,
            referred_by=referred_by,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_username(self, user: User, username: str | None) -> None:
        user.username = username
        await self.session.flush()

    async def save_survey(self, user: User, age: int, favorite_sport: str) -> None:
        user.age = age
        user.favorite_sport = favorite_sport
        await self.session.flush()

    async def count_referred(self, inviter_user_id: int) -> int:
        query = select(func.count(User.id)).where(User.referred_by == inviter_user_id)
        result = await self.session.scalar(query)
        return int(result or 0)

    async def count_referred_with_survey(self, inviter_user_id: int) -> int:
        query = select(func.count(User.id)).where(
            and_(
                User.referred_by == inviter_user_id,
                User.age.is_not(None),
                User.favorite_sport.is_not(None),
            )
        )
        result = await self.session.scalar(query)
        return int(result or 0)
