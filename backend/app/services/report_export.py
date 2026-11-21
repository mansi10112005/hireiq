"""Report export: JSON and PDF.

SECURITY: every piece of text that comes from a resume or job description is UNTRUSTED. ReportLab
paragraphs understand markup (even an <img> tag), so untrusted text is cleaned and ESCAPED before
it goes into the PDF. Markup is only used in strings written by us.
"""

import io
import json
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.analysis import AnalysisReport, SkillMatch, SummaryStatement

ORIGIN_LABEL = {
    "resume": "from the resume",
    "derived": "computed by HireIQ",
    "ai": "AI-written, needs review",
}
LEVEL_LABEL = {"strong": "Strong evidence", "moderate": "Moderate evidence", "limited": "Limited evidence"}
IMPORTANCE_LABEL = {"required": "Required", "preferred": "Preferred", "unspecified": "Mentioned"}
STATUS_GROUPS = [
    ("supported", "Supported (shown in use)"),
    ("partial", "Partially supported (only listed in Skills)"),
    ("unverified", "Unverified (no evidence found)"),
]

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_base = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=_base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#475569"))
H1 = ParagraphStyle("H1", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=0)
H2 = ParagraphStyle(
    "H2", parent=BODY, fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#0f172a"),
)
H3 = ParagraphStyle("H3", parent=BODY, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=14, bulletIndent=2)
EVIDENCE = ParagraphStyle("Evidence", parent=SMALL, leftIndent=14)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.5, leading=11)

CONTENT_WIDTH_MM = 174  # A4 (210 mm) minus 2 x 18 mm margins


def _clean(text: str | None, limit: int = 600) -> str:
    """Make untrusted text safe: strip control characters, keep the encoding the built-in
    font supports (anything else becomes '?'), then escape markup characters."""
    if not text:
        return ""
    text = _CONTROL_CHARS.sub("", text)[:limit]
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    return escape(text)


def _para(text: str | None, style: ParagraphStyle = BODY) -> Paragraph:
    """A paragraph whose text is UNTRUSTED (escaped)."""
    return Paragraph(_clean(text), style)


def _markup(markup: str, style: ParagraphStyle = BODY) -> Paragraph:
    """A paragraph from markup WE wrote. Never put untrusted text in here without _clean()."""
    return Paragraph(markup, style)


def _cell(text: str | None) -> Paragraph:
    return Paragraph(_clean(text, 300), CELL)


def _header_cell(label: str) -> Paragraph:
    return Paragraph(f"<b>{label}</b>", CELL)


def _table(rows: list[list], widths_mm: list[float]) -> Table:
    table = Table(rows, colWidths=[w * mm for w in widths_mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _format_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    except ValueError:
        return iso


def _skill_rows(matches: list[SkillMatch]) -> list[list]:
    rows: list[list] = [[_header_cell("Skill"), _header_cell("Importance"), _header_cell("Evidence from the resume")]]
    for match in matches:
        if match.evidence:
            evidence = "; ".join(f"\u201c{e.snippet}\u201d" for e in match.evidence[:2])
        else:
            evidence = "No evidence found"
        rows.append([_cell(match.name), _cell(IMPORTANCE_LABEL[match.importance]), _cell(evidence)])
    return rows


def _statements(title: str, items: list[SummaryStatement]) -> list:
    if not items:
        return []
    story: list = [_markup(title, H3)]
    for item in items:
        story.append(
            Paragraph(
                f"{_clean(item.text)} <font size='7.5' color='#475569'>[{ORIGIN_LABEL[item.origin]}]</font>",
                BULLET,
                bulletText="\u2022",
            )
        )
        if item.evidence:
            first = item.evidence[0]
            story.append(
                Paragraph(f"Evidence ({_clean(first.section or first.source)}): \u201c{_clean(first.snippet)}\u201d", EVIDENCE)
            )
    return story


def _build_story(report: AnalysisReport) -> list:
    story: list = []
    score = report.score

    story.append(_markup("HIREIQ CANDIDATE REPORT", SMALL))
    story.append(_para(report.candidate_name or "Unnamed candidate", H1))
    story.append(
        _para(f"{report.job_title or 'Untitled job'}  |  analysed {_format_time(report.created_at)}", BODY)
    )

    if report.warnings:
        story.append(_markup("Warnings", H2))
        for warning in report.warnings:
            story.append(Paragraph(_clean(warning), BULLET, bulletText="\u2022"))

    # ---- Score ----
    story.append(_markup("Match score", H2))
    if score.status == "calculated" and score.value is not None:
        level = LEVEL_LABEL.get(score.evidence_level or "", "")
        story.append(_markup(f"<b>{score.value}/100</b> - {escape(level)}", BODY))
    else:
        story.append(_markup("No score could be calculated for this job description.", BODY))
    story.append(_para(score.disclaimer, SMALL))

    rows: list[list] = [
        [_header_cell("Criterion"), _header_cell("Weight used"), _header_cell("Evidenced"), _header_cell("Points")]
    ]
    for component in score.components:
        if component.applicable and component.fraction is not None:
            rows.append(
                [
                    _cell(component.label),
                    _cell(f"{component.effective_weight:.1f}%"),
                    _cell(f"{round(component.fraction * 100)}%"),
                    _cell(f"{component.points:.1f}"),
                ]
            )
        else:
            rows.append([_cell(component.label), _cell("n/a"), _cell("n/a"), _cell("0")])
    story.append(Spacer(1, 4))
    story.append(_table(rows, [78, 30, 30, 36]))
    for note in score.notes:
        story.append(Paragraph(_clean(note), BULLET, bulletText="\u2022"))

    # ---- Skills ----
    story.append(_markup("Skills and evidence", H2))
    if not report.skill_matches.matches:
        story.append(_markup("No skills were recognised in the job description.", BODY))
    for status, title in STATUS_GROUPS:
        group = [m for m in report.skill_matches.matches if m.status == status]
        if not group:
            continue
        story.append(_markup(f"{title} - {len(group)}", H3))
        story.append(_table(_skill_rows(group), [46, 24, 104]))
    story.append(
        _markup(
            "Unverified means no evidence was found in the resume. It does not prove the "
            "candidate lacks the skill.",
            SMALL,
        )
    )

    # ---- Summary ----
    story.append(_markup("Candidate summary", H2))
    summary = report.summary
    professional = [summary.professional_summary] if summary.professional_summary else []
    story += _statements("Professional summary", professional)
    story += _statements("Key strengths (skills shown in use)", summary.key_strengths)
    story += _statements("Experience", summary.experience_overview)
    story += _statements("Projects", summary.project_overview)
    story += _statements("Education", summary.education_overview)

    # ---- Evaluation ----
    if report.evaluation.relevant_entries:
        story.append(_markup("Relevant experience and projects", H2))
        for entry in report.evaluation.relevant_entries:
            story.append(
                Paragraph(
                    f"<b>{_clean(entry.heading, 200)}</b> - matched: {_clean(', '.join(entry.matched_skills))}",
                    BULLET,
                    bulletText="\u2022",
                )
            )
            if entry.explanation:
                story.append(Paragraph(f"AI explanation: {_clean(entry.explanation)}", EVIDENCE))
            story.append(Paragraph(f"Evidence: \u201c{_clean(entry.evidence.snippet)}\u201d", EVIDENCE))

    # ---- Interview questions ----
    if report.interview_questions:
        story.append(_markup("Suggested interview questions", H2))
        for number, question in enumerate(report.interview_questions, start=1):
            story.append(Paragraph(_clean(question), BULLET, bulletText=f"{number}."))

    # ---- External research (kept separate) ----
    story.append(_markup("External research", H2))
    story.append(_para(f"{report.web_intelligence.status.replace('_', ' ').capitalize()}: {report.web_intelligence.note}", BODY))
    story.append(_markup("External information is kept separate from resume-based findings and never changes the score.", SMALL))

    # ---- How it was produced ----
    story.append(_markup("How this report was produced", H2))
    if report.ai_usage.llm_configured:
        used = ", ".join(report.ai_usage.nodes_using_ai) or "none"
        story.append(_para(f"AI model: {report.ai_usage.model}. Steps that used AI: {used}.", BODY))
        story.append(_para(report.ai_usage.note, SMALL))
    else:
        story.append(_markup("AI was not used. Everything came from rule-based parsing.", BODY))
    story.append(_para("Steps that ran: " + ", ".join(report.pipeline), SMALL))

    # ---- Limitations ----
    story.append(_markup("Limitations", H2))
    for item in report.limitations:
        story.append(Paragraph(_clean(item, 800), BULLET, bulletText="\u2022"))

    return story


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(
        18 * mm,
        10 * mm,
        "HireIQ report - a screening aid, not a hiring decision. AI-written text must be reviewed by a human.",
    )
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def export_report_pdf(report: AnalysisReport) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="HireIQ candidate report",  # no personal data in the file metadata
        author="HireIQ",
    )
    document.build(_build_story(report), onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def export_report_json(report: AnalysisReport) -> bytes:
    payload = {
        "format": "hireiq-report/1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "report": report.model_dump(mode="json"),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")