from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Playmaker_Picks_User_Guide.pdf"

pdfmetrics.registerFont(TTFont("SegoeUI", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SegoeUISymbol", r"C:\Windows\Fonts\seguisym.ttf"))

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
    name="Icon", parent=styles["BodyText"], fontName="SegoeUISymbol", fontSize=16,
    leading=18, textColor=colors.HexColor("#0b7285"), alignment=TA_CENTER,
))


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def section(icon, title, body):
    table = Table([[p(icon, "Icon"), p(f"<b>{title}</b>", "Section")]], colWidths=[0.35 * inch, 6.6 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [table, p(body)]


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.6 * inch,
        leftMargin=0.6 * inch, topMargin=0.5 * inch, bottomMargin=0.45 * inch,
        title="Playmaker Picks User Guide",
    )
    story = [
        p("Playmaker Picks", "TitleCustom"),
        p("Official play recording and results guide", "Subtitle"),
    ]
    story += section("📷", "Automatic image flow", "<b>1.</b> Upload a betting-slip image in the configured image channel. <b>2.</b> The bot reads the selections, decimal/American odds, team, and units. <b>3.</b> The bot posts <b>User Reviewing Bet</b> with a <b>Review image</b> button. <b>4.</b> Review the private/temporary review and confirm. <b>5.</b> The bot records the play against the original image message and removes the review message. It does not repost the bet." )
    story += section("✍", "Manual play entry", "Use <b>/play</b> when there is no image. Enter units, number of legs, Leg 1 selection, Leg 1 odds, and the optional team. Additional legs are entered one at a time. Each leg and its odds are stored, then combined when the final leg is submitted." )
    story += section("🧪", "Testing without recording", "Configure <b>TEST_CHANNEL_ID</b>, then use the protected command <b>/testing enabled:true</b>. Upload an image in the test channel. The bot parses the image and shows the result without writing to the database, posting a bet, or requiring confirmation. Use <b>Enter units</b> if the caption/image does not show units, then <b>Complete test</b>. Disable testing with <b>/testing enabled:false</b>. Only configured operators or server managers can change the runtime toggle; a restart restores the default state." )
    story += section("✏", "Editing a recorded bet", "The confirmation channel receives a <b>Recorded Bet</b> embed with an <b>Edit bet</b> button. Only the original user can edit it. The edit form loads each leg from the database, accepts one selection and one odds value per line, recalculates combined odds, and updates the stored play." )
    story += section("✅", "Results and reactions", "The original user can react to the original bet message: <b>✅ Win</b>, <b>❌ Loss</b>, <b>🅿️ Void</b>, or <b>🌓 Partial</b>. Win, loss, and void settle immediately. Partial sends a private follow-up for the remaining details." )
    story += section("📊", "Tracker updates", "Use <b>/update_tracker</b> from any channel. It reads the original unit tracker tables, updates the existing Unit Summary message in <b>RESULT_CHANNEL_ID</b>, and sends only the separate Top Playmakers embed to <b>TEAM_STATS_CHANNEL_ID</b>." )
    story += section("🔧", "If something does not appear", "Check that the bot is online, the user has the required official role, the image channel is configured, and the bot has permission to read messages, send messages, manage messages, and send direct messages. For deployment updates, pull the latest code and restart the systemd service." )
    story += [Spacer(1, 8), p("Quick configuration keys: IMAGE_INPUT_CHANNEL_ID • TEST_CHANNEL_ID • TESTING • TRACKING_CHANNEL_ID • RESULT_CHANNEL_ID • TEAM_STATS_CHANNEL_ID", "Small")]
    doc.build(story)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
