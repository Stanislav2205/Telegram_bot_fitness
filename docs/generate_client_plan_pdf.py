from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


OUTPUT_PATH = "D:/My_project/Bot/Telegram/docs/Plan_dlya_zakazchika.pdf"
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/arialbd.ttf"


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Arial", FONT_PATH))
    pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_BOLD_PATH))


def draw_title(c: canvas.Canvas, y: float) -> float:
    c.setFont("Arial-Bold", 18)
    c.drawString(20 * mm, y, "План запуска Telegram-розыгрыша")
    y -= 8 * mm
    c.setFont("Arial", 11)
    c.drawString(20 * mm, y, "Простое описание проекта")
    return y - 8 * mm


def draw_section_title(c: canvas.Canvas, y: float, text: str) -> float:
    c.setFont("Arial-Bold", 13)
    c.drawString(20 * mm, y, text)
    return y - 6 * mm


def draw_bullets(c: canvas.Canvas, y: float, items: list[str], line_gap_mm: float = 5.5) -> float:
    c.setFont("Arial", 11)
    for item in items:
        c.drawString(24 * mm, y, f"- {item}")
        y -= line_gap_mm * mm
    return y - 1 * mm


def draw_flow_boxes(c: canvas.Canvas, y_top: float) -> float:
    c.setFont("Arial-Bold", 12)
    c.drawString(20 * mm, y_top, "Схема 1: путь участника")
    y = y_top - 9 * mm

    boxes = [
        "1) Пользователь заходит в бота из поста",
        "2) Бот выдает личную ссылку для друзей",
        "3) Друг заходит по ссылке и стартует бота",
        "4) Бот проверяет подписку на канал",
        "5) Подтвержденный друг дает +1 билет",
    ]
    box_w = 168 * mm
    box_h = 12 * mm
    x = 20 * mm

    for idx, text in enumerate(boxes):
        c.setStrokeColor(colors.darkblue)
        c.setFillColor(colors.whitesmoke)
        c.roundRect(x, y - box_h, box_w, box_h, 2 * mm, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Arial", 10.3)
        c.drawString(x + 3 * mm, y - 8 * mm, text)
        if idx < len(boxes) - 1:
            c.setStrokeColor(colors.gray)
            c.line(x + box_w / 2, y - box_h - 1.5 * mm, x + box_w / 2, y - box_h - 5.5 * mm)
            c.line(x + box_w / 2, y - box_h - 5.5 * mm, x + box_w / 2 - 1.7 * mm, y - box_h - 3.8 * mm)
            c.line(x + box_w / 2, y - box_h - 5.5 * mm, x + box_w / 2 + 1.7 * mm, y - box_h - 3.8 * mm)
        y -= 18 * mm
    return y


def draw_roadmap(c: canvas.Canvas, y_top: float) -> float:
    c.setFont("Arial-Bold", 12)
    c.drawString(20 * mm, y_top, "Схема 2: этапы запуска")
    y = y_top - 12 * mm
    x_start = 24 * mm
    step_w = 38 * mm
    step_h = 14 * mm
    gap = 6 * mm
    steps = ["Настроить", "Проверить", "Запустить", "Подвести итоги"]

    for i, step in enumerate(steps):
        x = x_start + i * (step_w + gap)
        c.setFillColor(colors.lightgrey)
        c.rect(x, y - step_h, step_w, step_h, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Arial", 9.6)
        c.drawCentredString(x + step_w / 2, y - 9 * mm, step)
        if i < len(steps) - 1:
            x1 = x + step_w + 1 * mm
            x2 = x + step_w + gap - 1 * mm
            y_mid = y - step_h / 2
            c.line(x1, y_mid, x2, y_mid)
            c.line(x2, y_mid, x2 - 1.8 * mm, y_mid + 1.2 * mm)
            c.line(x2, y_mid, x2 - 1.8 * mm, y_mid - 1.2 * mm)
    return y - 20 * mm


def generate() -> None:
    register_fonts()
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    _, height = A4
    y = height - 20 * mm

    y = draw_title(c, y)
    y = draw_section_title(c, y, "1. Цель проекта")
    y = draw_bullets(
        c,
        y,
        [
            "Увеличить число подписчиков канала.",
            "Поднять лояльность: не только привлечь людей, но и удержать их.",
            "Сделать прозрачную механику без ручного подсчета.",
        ],
    )

    y = draw_section_title(c, y, "2. Как работает розыгрыш")
    y = draw_bullets(
        c,
        y,
        [
            "В канале публикуется пост с призом и сроками.",
            "Пользователь открывает бота и получает личную ссылку.",
            "Каждый друг, который подписался и прошел проверку, дает +1 шанс.",
            "В конце бот автоматически выбирает победителей.",
        ],
    )

    y = draw_flow_boxes(c, y)
    if y < 80 * mm:
        c.showPage()
        y = height - 20 * mm

    y = draw_section_title(c, y, "3. Защита от накрутки")
    y = draw_bullets(
        c,
        y,
        [
            "Нельзя засчитать приглашение самому себе.",
            "Один человек учитывается только один раз.",
            "Билет начисляется только после проверки подписки.",
            "Слишком частые запросы бот временно ограничивает.",
        ],
    )

    y = draw_section_title(c, y, "4. Как проходит сам розыгрыш")
    y = draw_bullets(
        c,
        y,
        [
            "В день завершения бот фиксирует список участников с билетами.",
            "Проверяются условия: подписка активна, дубликатов и нарушений нет.",
            "Из всех билетов случайно выбирается победитель (или несколько).",
            "Результат сохраняется в журнале, чтобы можно было проверить честность.",
            "В канале публикуется пост с итогами и инструкцией для получения приза.",
        ],
    )
    c.save()


if __name__ == "__main__":
    generate()
