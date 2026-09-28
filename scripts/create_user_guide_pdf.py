from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Playmaker_Picks_User_Guide.pdf"
EMOJI_FONT = r"C:\Windows\Fonts\seguiemj.ttf"
# Segoe UI Emoji stores its color layers at 109px; other sizes render flat.
EMOJI_RENDER_PX = 109


@lru_cache(maxsize=32)
def _emoji_png(character: str) -> bytes:
    font = ImageFont.truetype(EMOJI_FONT, EMOJI_RENDER_PX)
    canvas = PILImage.new("RGBA", (EMOJI_RENDER_PX * 2, EMOJI_RENDER_PX * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text((EMOJI_RENDER_PX // 4, EMOJI_RENDER_PX // 4), character, font=font, embedded_color=True)
    bounds = canvas.getbbox()
    if bounds is None:
        raise ValueError(f"Emoji {character!r} rendered blank")
    buffer = BytesIO()
    canvas.crop(bounds).save(buffer, "PNG")
    return buffer.getvalue()


def emoji(character: str, size: float) -> RLImage:
    image = RLImage(BytesIO(_emoji_png(character)))
    ratio = image.imageHeight / image.imageWidth
    image.drawWidth = size
    image.drawHeight = size * ratio
    return image


pdfmetrics.registerFont(TTFont("SegoeUI", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SegoeUIEmoji", r"C:\Windows\Fonts\seguiemj.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="TitleCustom", parent=styles["Title"], fontName="SegoeUI", fontSize=22,
    leading=26, textColor=colors.HexColor("#243b53"), alignment=TA_CENTER, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Subtitle", parent=styles["Normal"], fontName="SegoeUI", fontSize=10,
    leading=14, textColor=colors.HexColor("#52606d"), alignment=TA_CENTER, spaceAfter=16,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading2"], fontName="SegoeUI", fontSize=13,
    leading=17, textColor=colors.HexColor("#0b7285"), spaceBefore=8, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontName="SegoeUI", fontSize=9.5,
    leading=14, textColor=colors.HexColor("#263238"), spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="Small", parent=styles["BodyText"], fontName="SegoeUI", fontSize=8,
    leading=11, textColor=colors.HexColor("#52606d"),
))
styles.add(ParagraphStyle(
    name="Icon", parent=styles["BodyText"], fontName="SegoeUIEmoji", fontSize=16,
    leading=18, textColor=colors.HexColor("#0b7285"), alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="CellIcon", parent=styles["BodyText"], fontName="SegoeUIEmoji", fontSize=12,
    leading=15, textColor=colors.HexColor("#263238"), alignment=TA_CENTER,
))


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def section(icon, title, body):
    table = Table([[emoji(icon, 0.24 * inch), p(f"<b>{title}</b>", "Section")]], colWidths=[0.35 * inch, 6.6 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [table, p(body)]


def command_table(rows, headers, col_widths, icon_column=False):
    data = [[p(f"<b>{header}</b>", "Small") for header in headers]]
    for row in rows:
        cells = [p(cell, "Small") for cell in row]
        if icon_column:
            cells[0] = emoji(row[0], 0.2 * inch)
        data.append(cells)
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f2f5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0b7285")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "CENTER" if icon_column else "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d3da")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f9fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [table, Spacer(1, 8)]


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.6 * inch,
        leftMargin=0.6 * inch, topMargin=0.5 * inch, bottomMargin=0.45 * inch,
        title="Playmaker Picks User Guide",
    )
    story = [
        p("Playmaker Picks", "TitleCustom"),
        p("Command reference and results guide", "Subtitle"),
    ]

    story += section("📷", "Recording a play from an image", "Post your betting-slip image in the plays channel. No command is needed. The bot reads the selections, odds, and units, then shows you a private preview. Press <b>Confirm and record</b> to post the play card publicly. If the slip does not show your units, press <b>Enter units</b> first, then confirm.")
    story += section("✍️", "Recording a play manually", "Use <b>/play</b> when you have no image. You need an official role and must run it in the official plays channel. Enter your units, the number of legs, the Leg 1 selection, the Leg 1 odds, and an optional team. Multi-leg plays prompt for each remaining leg one at a time, and the combined odds are calculated automatically when the final leg is submitted.")

    story += section("✅", "Settling a play with reactions", "React directly on the play card in the official channel. The play owner and anyone holding an operator role can settle. Reactions posted in any other channel are ignored.")
    story += command_table(
        [
            ["✅", "Win", "Settles immediately and updates the card"],
            ["❌", "Loss", "Settles immediately and updates the card"],
            ["🅿️", "Void", "No change to your unit total"],
            ["🌓", "Partial", "Not processed by reaction — use /settle instead"],
        ],
        ["Icon", "Result", "What happens"],
        [0.55 * inch, 1.0 * inch, 5.4 * inch],
        icon_column=True,
    )

    story += section("🛠️", "Commands for everyone", "")
    story += command_table(
        [
            ["/update_tracker", "Refreshes the Unit Summary now and catches up any missed reactions. The tracker also refreshes automatically every hour, Eastern Time."],
            ["/rankings", "Posts the current team ranking summary."],
            ["/summary", "Posts the daily playmaker report with the top three finishers."],
            ["/tracker_start date_value:show", "Shows the date the tracker is currently counting from."],
            ["/test", "Runs system diagnostics. Attach an image to parse it without recording anything."],
        ],
        ["Command", "What it does"],
        [2.1 * inch, 4.85 * inch],
    )

    story += section("🔒", "Commands for officials", "")
    story += command_table(
        [
            ["/settle play_id: result:", "Settles a play. Accepts win, loss, void, partial, or regraded. Use this for partials and for any play whose card was deleted. The play ID is the number shown on the card as &quot;Play #43&quot;."],
            ["/regrade play_id: legs_left: odds: [note:]", "Use when a leg voids and the rest of the parlay stands. Sets the remaining leg count and the new odds. Regraded plays count as zero units."],
        ],
        ["Command", "What it does"],
        [2.1 * inch, 4.85 * inch],
    )

    story += [PageBreak()]
    story += section("🔑", "Commands for operators and server managers", "")
    story += command_table(
        [
            ["/tracker_start date_value:YYYY-MM-DD", "Counts only plays settled on or after this date, for example 2026-09-28. Everything earlier is hidden from the tracker but is never deleted."],
            ["/tracker_start date_value:clear", "Counts every play again."],
            ["/testing enabled:true", "Sends parsed plays to the lab channel without writing to the database."],
            ["/testing enabled:false", "Returns to normal recording."],
        ],
        ["Command", "What it does"],
        [2.55 * inch, 4.4 * inch],
    )
    story += [p("Both settings revert to their .env defaults when the bot restarts. Set TRACKER_START_DATE or TESTING in .env to make a change permanent.", "Small"), Spacer(1, 8)]

    story += section("📊", "How units are scored", "Wins pay the true price of the bet. Risking 2 units at +250 and winning returns <b>+5 units</b>; the same 2 units at −110 returns <b>+1.82 units</b>. A loss always costs the full amount risked. Voids and regrades count as zero. Your record displays as wins-losses, and the net unit figure reflects actual profit rather than a flat win count.")

    story += section("\U0001F6A8", "If something does not appear", "Check that the bot is online, that you hold the required official role, and that you are posting in the correct channel. Plays only record in the official plays channel, and only reactions in that channel settle a play. If a result will not settle by reaction, ask an official to run <b>/settle</b>. After a deployment, pull the latest code and restart the service.")

    doc.build(story)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
