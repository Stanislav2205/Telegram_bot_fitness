#!/usr/bin/env python3
"""
Скрипт для очистки всей базы данных
Удаляет все данные из всех таблиц, но сохраняет структуру таблиц
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.db.models import Base


async def clear_database():
    """
    Очищает все данные из базы данных, но сохраняет структуру таблиц
    """
    print("⚠️  ВНИМАНИЕ: Этот скрипт удалит все данные из базы данных!")
    print("   Это действие невозможно отменить.")
    
    response = input("   Продолжить? (введите 'yes' для подтверждения): ")
    if response.lower() != 'yes':
        print("❌ Очистка отменена.")
        return False
    
    settings = get_settings()
    engine = create_async_engine(settings.db_dsn)
    
    try:
        print("🚀 Начинаем очистку базы данных...")
        
        # Получаем список всех таблиц в правильном порядке (с учетом зависимостей)
        async with engine.connect() as conn:
            # Для PostgreSQL удаляем данные в правильном порядке с учетом внешних ключей
            # Удаляем сначала таблицы, которые ссылаются на другие, затем те, на которые ссылаются
            # Удаляем данные в правильном порядке с учетом внешних ключей
            # Начинаем с таблиц, которые ссылаются на другие (зависимые)
            table_names = [
                'draw_results',      # Ссылается на campaigns и users
                'tickets',           # Ссылается на users и campaigns
                'referrals',         # Ссылается на users и campaigns
                'audit_logs',        # Может ссылаться на users
                'campaigns',         # Не зависит от других наших таблиц
                'users'              # Может быть родительской для других таблиц
            ]
            
            for table_name in table_names:
                try:
                    await conn.execute(text(f"DELETE FROM {table_name};"))
                    await conn.commit()  # Фиксируем транзакцию после каждой операции
                    print(f"✅ Очищена таблица: {table_name}")
                except Exception as e:
                    print(f"⚠️  Ошибка при очистке таблицы {table_name}: {e}")
                    await conn.rollback()  # Откатываем в случае ошибки
        
        print("✅ База данных успешно очищена!")
        print("ℹ️  Структура таблиц сохранена, можно продолжать работу.")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await engine.dispose()


async def clear_database_with_recreate():
    """
    Очищает базу данных и заново создает все таблицы
    """
    print("⚠️  ВНИМАНИЕ: Этот скрипт удалит все данные и заново создаст таблицы!")
    print("   Это действие невозможно отменить.")
    
    response = input("   Продолжить? (введите 'yes' для подтверждения): ")
    if response.lower() != 'yes':
        print("❌ Очистка отменена.")
        return False
    
    settings = get_settings()
    engine = create_async_engine(settings.db_dsn)
    
    try:
        print("🚀 Начинаем полную пересоздание базы данных...")
        
        async with engine.begin() as conn:
            # Удаляем все таблицы
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ Все таблицы удалены")
            
            # Создаем все таблицы заново
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Все таблицы созданы заново")
        
        print("✅ База данных полностью пересоздана!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при пересоздании базы данных: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await engine.dispose()


def main():
    print("🗑️  Скрипт очистки базы данных")
    print("=" * 50)
    print("Доступные режимы:")
    print("  1. Очистка данных (сохранить структуру таблиц)")
    print("  2. Полное пересоздание базы данных (очистка + создание новых таблиц)")
    print("")
    
    choice = input("Выберите режим (1 или 2): ").strip()
    
    if choice == "1":
        success = asyncio.run(clear_database())
    elif choice == "2":
        success = asyncio.run(clear_database_with_recreate())
    else:
        print("❌ Неверный выбор. Используйте 1 или 2.")
        return
    
    if success:
        print("✅ Очистка завершена успешно!")
    else:
        print("❌ Произошла ошибка при очистке.")


if __name__ == "__main__":
    main()