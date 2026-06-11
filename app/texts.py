DRAW_START_ANNOUNCEMENT = (
    "Привет всем подписчикам канала OnerFitness и участникам розыгрыша. "
    "Прямо сейчас проводим розыгрыш приза — не пропустите!"
)


def build_draw_launch_announcement(bot_username: str) -> str:
    participation_link = f"https://t.me/{bot_username}"
    return (
        "🔥 Розыгрыш запущен!\n\n"
        "Участвуйте прямо сейчас и приглашайте друзей.\n"
        f"Ссылка на участие: {participation_link}\n\n"
        "Нажмите /start в боте, чтобы зарегистрироваться."
    )
