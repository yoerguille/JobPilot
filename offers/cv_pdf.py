import re
from io import BytesIO
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate

from .cv_ai import SECTION_TITLES


PDF_STYLE_VERSION = 2
SECTION_ORDER = ("summary", "projects", "skills", "experience", "education", "languages")
ENTRY_SECTIONS = {"projects", "experience", "education"}


def render_cv_pdf(content):
    profile = content["profile"]
    english = content.get("language") == "en"
    navy = colors.HexColor("#10264A")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, title=f'CV - {profile["full_name"]}',
        leftMargin=32, rightMargin=32, topMargin=24, bottomMargin=32,
    )
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=11.5, leading=15.5, textColor=colors.HexColor("#111111"))
    name = ParagraphStyle("Name", parent=body, fontName="Helvetica-Bold", fontSize=28, leading=31, spaceAfter=4, keepWithNext=True)
    headline = ParagraphStyle("Headline", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=19, spaceAfter=9, keepWithNext=True)
    contact = ParagraphStyle("Contact", parent=body, fontSize=11, leading=14)
    section = ParagraphStyle(
        "Section", parent=body, fontName="Helvetica-Bold", fontSize=15.5, leading=19,
        textColor=navy, spaceBefore=25, keepWithNext=True,
    )
    entry_title = ParagraphStyle("Entry", parent=body, spaceBefore=5)
    entry_with_details = ParagraphStyle("EntryWithDetails", parent=entry_title, keepWithNext=True)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=23, bulletIndent=7)
    story = []

    def add(text, style=body):
        if text:
            story.append(Paragraph("<br/>".join(escape(line) for line in text.splitlines()), style))

    def add_heading(key):
        labels = {
            "summary": ("Perfil profesional", "Professional profile"),
            "skills": ("Tecnologías", "Technologies"),
            "experience": ("Experiencia profesional", "Professional experience"),
        }
        add(labels.get(key, SECTION_TITLES[key])[english].upper(), section)
        rule = HRFlowable(width="100%", thickness=1.25, color=navy, spaceBefore=4, spaceAfter=7)
        rule.keepWithNext = True
        story.append(rule)

    def add_bullet(text):
        story.append(Paragraph(escape(text), bullet, bulletText="•"))

    def add_entry(title, details, has_description=False):
        markup = " | ".join([f"<b>{escape(title)}</b>", *(escape(value) for value in details if value)])
        story.append(Paragraph(markup, entry_with_details if has_description else entry_title))

    add(profile["full_name"].upper(), name)
    add(profile.get("headline", "").upper(), headline)
    contact_parts = [escape(profile[key]) for key in ("location", "email", "phone") if profile.get(key)]
    for key, label in (("portfolio_url", "Portfolio"), ("linkedin_url", "LinkedIn"), ("github_url", "GitHub")):
        if url := profile.get(key):
            text = escape(re.sub(r"^https?://", "", url, flags=re.IGNORECASE))
            if urlsplit(url).scheme in {"http", "https"}:
                text = f'<a href={quoteattr(url)} color="#10264A"><u>{text}</u></a>'
            contact_parts.append(f"{label}: {text}")
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact))

    if "text_sections" in content:
        for key in SECTION_ORDER:
            if not (value := content["text_sections"].get(key)):
                continue
            add_heading(key)
            if key not in ENTRY_SECTIONS:
                add(" · ".join(value.splitlines()) if key in {"skills", "languages"} else value)
                continue
            lines = value.splitlines()
            for index, line in enumerate(lines):
                line = line.strip()
                if match := re.match(r"^[-*•]\s+(.*)", line):
                    add_bullet(match[1])
                elif line:
                    title, _, details = line.partition(" | ")
                    has_details = index + 1 < len(lines) and bool(re.match(r"^\s*[-*•]\s+", lines[index + 1]))
                    add_entry(title, [details], has_details)
    else:
        if profile.get("summary"):
            add_heading("summary")
            add(profile["summary"])
        for key in SECTION_ORDER[1:]:
            if not (entries := content.get(key)):
                continue
            add_heading(key)
            if key in {"skills", "languages"}:
                add(" · ".join(entries))
                continue
            title_field = {"projects": "name", "experience": "role", "education": "qualification"}[key]
            for item in entries:
                description = [line.strip() for line in item.get("description", "").splitlines() if line.strip()]
                add_entry(item[title_field], [
                    item.get("company"), item.get("institution"), item.get("period"), item.get("url"),
                ], bool(description))
                for line in description:
                    add_bullet(re.sub(r"^[-*•]\s+", "", line))

    document.build(story)
    return buffer.getvalue()
