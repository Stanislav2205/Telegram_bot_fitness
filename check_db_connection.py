#!/usr/bin/env python3
"""
Скрипт для проверки соединения с базой данных PostgreSQL
"""

import asyncio
from sqlalchemy import text
from app.db.session import build_engine
from app.config import get_settings


async def check_db_connection():
    print("Проверка соединения с базой данных...")
    try:
        settings = get_settings()
        engine = build_engine(settings)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
        await engine.dispose()
        print("[OK] Соединение с базой данных установлено!")
        return True
    except Exception as e:
        print(f"[FAIL] Ошибка подключения к базе данных: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(check_db_connection())
    exit(0 if success else 1)
