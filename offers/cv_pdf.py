from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate


def render_cv_pdf(content):
    profile = content["profile"]
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, title=f'CV - {profile["full_name"]}',
        leftMargin=48, rightMargin=48, topMargin=40, bottomMargin=40,
    )
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.5, leading=14, textColor=colors.HexColor("#172222"))
    name = ParagraphStyle("Name", parent=body, fontName="Helvetica-Bold", fontSize=26, leading=30, spaceAfter=5)
    section = ParagraphStyle(
        "Section", parent=body, fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=colors.HexColor("#165646"), spaceBefore=13, spaceAfter=4, keepWithNext=True,
    )
    entry_title = ParagraphStyle("Entry", parent=body, fontName="Helvetica-Bold", spaceBefore=5)
    story = []

    def add(text, style=body):
        if text:
            story.append(Paragraph("<br/>".join(escape(line) for line in text.splitlines()), style))

    add(profile["full_name"], name)
    add(profile.get("headline"))
    add(" · ".join(filter(None, (profile.get("location"), profile.get("email"), profile.get("phone")))))
    add(profile.get("portfolio_url"))
    if profile.get("summary"):
        add("Resumen profesional", section)
        add(profile["summary"])
    for key, label, fields in (
        ("experience", "Experiencia", ("role", "company")),
        ("projects", "Proyectos", ("name",)),
        ("education", "Formación", ("qualification", "institution")),
    ):
        if content[key]:
            add(label, section)
            for entry in content[key]:
                add(" · ".join(entry[field] for field in fields), entry_title)
                add(entry.get("period"))
                add(entry.get("url"))
                add(entry.get("description"))
    if content["skills"]:
        add("Habilidades", section)
        add(" · ".join(content["skills"]))
    document.build(story)
    return buffer.getvalue()
