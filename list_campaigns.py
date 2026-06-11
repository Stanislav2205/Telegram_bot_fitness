#!/usr/bin/env python3
"""
Скрипт для просмотра списка кампаний в базе данных.
Бот запущенным быть не обязательно — нужна только работающая база данных PostgreSQL.
"""

import asyncio
from sqlalchemy import select
from app.db.session import build_engine, build_session_factory
from app.db.models import Campaign
from app.config import get_settings


async def list_campaigns():
    settings = get_settings()
    session_factory = build_session_factory(settings)
    
    async with session_factory() as session:
        result = await session.execute(select(Campaign).order_by(Campaign.id))
        campaigns = result.scalars().all()
        
        if not campaigns:
            print("Кампаний не найдено.")
            return
        
        print("\n" + "=" * 80)
        print(f"{'ID':<5} {'Название':<35} {'Статус':<10} {'Начало':<12} {'Окончание':<12}")
        print("=" * 80)
        
        for c in campaigns:
            starts = c.starts_at.strftime("%d.%m.%Y") if c.starts_at else "-"
            ends = c.ends_at.strftime("%d.%m.%Y") if c.ends_at else "-"
            print(f"{c.id:<5} {c.title:<35} {c.status.value:<10} {starts:<12} {ends:<12}")
        
        print("=" * 80)
        print(f"Всего кампаний: {len(campaigns)}\n")


if __name__ == "__main__":
    asyncio.run(list_campaigns())
