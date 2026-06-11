from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_keyboard(channel_link: str | None) -> InlineKeyboardMarkup:
    rows = []
    if channel_link:
        rows.append([InlineKeyboardButton(text="Подписаться на канал", url=channel_link)])
    rows.append([InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Моя ссылка", callback_data="my_ref_link")],
            [InlineKeyboardButton(text="Мой прогресс", callback_data="my_progress")],
            [InlineKeyboardButton(text="Правила", callback_data="rules")],
        ]
    )
