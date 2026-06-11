#!/usr/bin/env python3
"""
Скрипт для проверки соединения с Telegram API
"""

import asyncio
import sys
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
import socket

from app.config import get_settings


async def check_bot_connection():
    """
    Функция для проверки соединения с Telegram API
    """
    print("Проверка соединения с Telegram API...")
    
    try:
        # Получаем настройки
        settings = get_settings()
        print(f"Имя бота: @{settings.bot_username}")
        print(f"Токен бота задан: {'Да' if settings.bot_token else 'Нет'}")
        
        if not settings.bot_token:
            print("[FAIL] Токен бота не задан в настройках")
            return False
        
        # Создаем сессию с учетом прокси и IPv4
        session = AiohttpSession(proxy=settings.telegram_proxy)
        session._connector_init["family"] = socket.AF_INET
        
        # Создаем объект бота
        bot = Bot(token=settings.bot_token, session=session)
        
        # Пробуем получить информацию о боте
        print("Получение информации о боте...")
        user_info = await bot.get_me()
        
        print("[OK] Соединение с Telegram API успешно установлено!")
        print(f"ID бота: {user_info.id}")
        print(f"Имя бота: {user_info.first_name}")
        print(f"Username: @{user_info.username}")
        print(f"Язык: {user_info.language_code}")
        
        # Проверим также возможность отправки сообщения самому себе (в режиме теста)
        try:
            # Получим информацию о канале
            if settings.channel_id:
                print(f"\nПроверка доступа к каналу: {settings.channel_id}")
                # Попробуем получить информацию о канале
                chat_info = await bot.get_chat(settings.channel_id)
                print(f"Название канала: {chat_info.title}")
                print("[OK] Доступ к каналу подтвержден")
        except Exception as e:
            print(f"[WARN] Не удалось получить информацию о канале: {e}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Ошибка соединения с Telegram API: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Закрываем сессию
        if 'bot' in locals():
            await bot.session.close()


def check_imports():
    """Проверка корректности импортов"""
    print("Проверка импортов...")
    try:
        from app.config import get_settings
        from aiogram import Bot
        from aiogram.client.session.aiohttp import AiohttpSession
        print("[OK] Все необходимые импорты прошли успешно")
        return True
    except ImportError as e:
        print(f"[FAIL] Ошибка импорта: {e}")
        return False


if __name__ == "__main__":
    print("Начинаем проверку соединения с Telegram API...")
    
    # Сначала проверяем импорты
    if not check_imports():
        sys.exit(1)
    
    # Затем проверяем соединение
    success = asyncio.run(check_bot_connection())
    sys.exit(0 if success else 1)