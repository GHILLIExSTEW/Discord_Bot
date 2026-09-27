from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKGROUND_PATH = Path(__file__).resolve().parents[1] / "Media" / "Growth.png"
IMAGE_WIDTH = 1200
HORIZONTAL_PADDING = 72
CARD_GAP = 24


@lru_cache(maxsize=8)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        (r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf")
    )
    for font_path in candidates:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)

    linux_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(linux_font, size=size)
    except OSError:
        return ImageFont.load_default(size=size)


def _plain_text(value: str) -> str:
    return re.sub(r"\*\*(.*?)\*\*", r"\1", value).strip()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        candidate = f"{current_line} {word}".strip()
        if current_line and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate
    if current_line:
        lines.append(current_line)
    return lines


def render_tracker_image(description: str, fields: list[tuple[str, str]], footer: str) -> BytesIO:
    breakdown_value = next((value for name, value in fields if "Playmaker Breakdown" in name), "")
    breakdown_rows = [
        _plain_text(row)
        for row in breakdown_value.split("\n\n")
        if row.strip() and "No settled plays yet" not in row
    ]

    row_font = _font(27)
    row_measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    wrapped_rows = [
        _wrap_text(row_measure, row, row_font, IMAGE_WIDTH - HORIZONTAL_PADDING * 2 - 28)
        for row in breakdown_rows
    ]
    row_heights = [max(58, len(lines) * 36 + 18) for lines in wrapped_rows]

    cards_top = 190
    cards_height = 164
    breakdown_top = 408
    rows_top = 475
    footer_height = 86
    image_height = max(760, rows_top + sum(row_heights) + footer_height)
    image_size = (IMAGE_WIDTH, image_height)

    background = ImageOps.fit(
        Image.open(BACKGROUND_PATH).convert("RGBA"),
        image_size,
        method=Image.Resampling.LANCZOS,
    )
    background.putalpha(62)
    canvas = Image.new("RGBA", image_size, (9, 20, 31, 0))
    canvas.alpha_composite(background)
    canvas.alpha_composite(Image.new("RGBA", image_size, (8, 18, 28, 164)))
    draw = ImageDraw.Draw(canvas, "RGBA")

    white = (248, 251, 255, 255)
    muted = (196, 211, 222, 255)
    accent = (104, 229, 194, 255)
    draw.text((HORIZONTAL_PADDING, 54), "UNIT TRACKER", font=_font(27, bold=True), fill=accent)
    draw.text((HORIZONTAL_PADDING, 101), _plain_text(description), font=_font(36, bold=True), fill=white)

    card_width = (IMAGE_WIDTH - HORIZONTAL_PADDING * 2 - CARD_GAP * 2) // 3
    for index, (name, value) in enumerate(fields[:3]):
        x = HORIZONTAL_PADDING + index * (card_width + CARD_GAP)
        y = cards_top
        draw.rounded_rectangle(
            (x, y, x + card_width, y + cards_height),
            radius=22,
            fill=(8, 19, 29, 190),
            outline=(255, 255, 255, 92),
            width=2,
        )
        label = name.replace("⏳", "").replace("📅", "").replace("🗓️", "").strip().upper()
        draw.text((x + 22, y + 20), label, font=_font(21, bold=True), fill=muted)
        value_text = _plain_text(value)
        value_font_size = 51
        while value_font_size > 30 and draw.textbbox((0, 0), value_text, font=_font(value_font_size, bold=True))[2] > card_width - 44:
            value_font_size -= 2
        draw.text((x + 22, y + 69), value_text, font=_font(value_font_size, bold=True), fill=white)

    breakdown_title = next((name for name, _ in fields if "Playmaker Breakdown" in name), "PLAYMAKER BREAKDOWN")
    breakdown_title = breakdown_title.replace("🏆", "").strip().upper()
    draw.text((HORIZONTAL_PADDING, breakdown_top), breakdown_title, font=_font(27, bold=True), fill=accent)

    row_y = rows_top
    if not wrapped_rows:
        draw.text((HORIZONTAL_PADDING, row_y), "No settled plays yet.", font=row_font, fill=muted)
    for lines, row_height in zip(wrapped_rows, row_heights):
        for line_index, line in enumerate(lines):
            draw.text(
                (HORIZONTAL_PADDING + 8, row_y + 4 + line_index * 36),
                line,
                font=row_font,
                fill=white,
            )
        row_y += row_height

    draw.text((HORIZONTAL_PADDING, image_height - 54), _plain_text(footer), font=_font(19), fill=muted)
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output