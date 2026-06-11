from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest


class SubscriptionService:
    ELIGIBLE_STATUSES = {"member", "administrator", "creator"}

    def __init__(self, bot: Bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id

    async def is_subscribed(self, user_id: int) -> bool:
        try:
            member = await self.bot.get_chat_member(chat_id=self.channel_id, user_id=user_id)
        except TelegramBadRequest:
            return False
        return member.status in self.ELIGIBLE_STATUSES
