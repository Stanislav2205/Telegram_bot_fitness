from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, action: str, details: str, actor_user_id: int | None = None, target_id: str | None = None) -> None:
        entry = AuditLog(
            action=action,
            details=details,
            actor_user_id=actor_user_id,
            target_id=target_id,
        )
        self.session.add(entry)
        await self.session.flush()
