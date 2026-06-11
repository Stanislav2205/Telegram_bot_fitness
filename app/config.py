from functools import lru_cache
from typing import Annotated, List
from datetime import datetime

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    bot_username: str
    channel_id: int
    channel_link: str
    db_dsn: str
    telegram_proxy: str | None = None
    redis_url: str | None = None
    admin_ids: Annotated[List[int], NoDecode] = []
    draw_timezone: str = "Europe/Moscow"
    run_mode: str = "polling"
    webhook_base_url: str = ""
    webhook_path: str = "/telegram/webhook"
    webhook_secret: str = ""
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    webhook_drop_pending_updates: bool = False
    # Добавляем новые параметры для периода активной сессии
    campaign_start_date: str = "01.06.2026"  # Дата начала кампании в формате ДД.ММ.ГГГГ
    campaign_end_date: str = "30.06.2026"    # Дата окончания кампании в формате ДД.ММ.ГГГГ

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int] | None) -> list[int]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [int(item.strip()) for item in value.split(",") if item.strip()]

    @field_validator("telegram_proxy", mode="before")
    @classmethod
    def parse_telegram_proxy(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("channel_id", mode="before")
    @classmethod
    def normalize_channel_id(cls, value: int | str) -> int:
        channel_id = int(str(value).strip().replace("\r", ""))
        if channel_id > 0:
            return -channel_id
        return channel_id

    @field_validator("channel_link", mode="before")
    @classmethod
    def normalize_channel_link(cls, value: str | None) -> str:
        if value is None:
            return ""
        return value.strip().replace("\r", "")

    @field_validator("run_mode")
    @classmethod
    def validate_run_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"polling", "webhook"}:
            raise ValueError("RUN_MODE must be either 'polling' or 'webhook'")
        return normalized

    @field_validator("webhook_path")
    @classmethod
    def validate_webhook_path(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = f"/{value}"
        return value

    @field_validator("campaign_start_date", "campaign_end_date", mode="before")
    @classmethod
    def validate_date_format(cls, value: str) -> str:
        """Проверяет формат даты ДД.ММ.ГГГГ"""
        if value is None:
            return value
        try:
            datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            raise ValueError(f"Date must be in DD.MM.YYYY format, got: {value}")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()