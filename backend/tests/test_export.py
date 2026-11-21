"""Export tests: JSON, PDF, and PDF safety against hostile resume text."""

import json
from pathlib import Path

import pymupdf

from app.services.report_export import export_report_json, export_report_pdf
from app.workflows.graph import build_workflow

SAMPLES = Path(__file__).parent / "sample_files"
JOB_TEXT = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")


def make_report():
    state = {
        "filename": "candidate.txt",
        "file_bytes": (SAMPLES / "sample_resume.txt").read_bytes(),
        "job_title": "Backend Developer",
        "job_description": JOB_TEXT,
        "enable_web_research": False,
        "web_research_consent": False,
        "warnings": [],
        "completed_nodes": [],
    }
    return build_workflow().invoke(state)["report"]


def pdf_text(data: bytes) -> str:
    with pymupdf.open(stream=data, filetype="pdf") as document:
        return "\n".join(page.get_text() for page in document)


def test_json_export_wraps_the_report_with_a_format_marker():
    report = make_report()

    payload = json.loads(export_report_json(report))

    assert payload["format"] == "hireiq-report/1"
    assert payload["report"]["analysis_id"] == report.analysis_id
    assert payload["report"]["score"]["value"] == 67
    assert "gsk_" not in json.dumps(payload)  # no API keys anywhere


def test_pdf_export_is_a_readable_pdf_with_the_key_content():
    data = export_report_pdf(make_report())

    assert data.startswith(b"%PDF-")
    text = pdf_text(data)
    assert "Jane Example" in text
    assert "67/100" in text
    assert "Limitations" in text
    assert "not a hiring decision" in text


def test_pdf_export_treats_resume_text_as_text_not_markup():
    report = make_report()
    hostile = '<img src="file:///C:/Windows/win.ini"/> <b>Bold?</b> & <script>x</script>'
    report = report.model_copy(update={"candidate_name": hostile})

    data = export_report_pdf(report)  # must not raise, and must not load the "image"

    text = pdf_text(data)
    assert "<img" in text  # shown literally, not interpreted
    assert "<b>Bold?</b>" in text


def test_pdf_export_survives_characters_the_built_in_font_cannot_draw():
    report = make_report().model_copy(update={"candidate_name": "Zoë Łukasz 张伟"})

    text = pdf_text(export_report_pdf(report))

    assert "Zo" in text  # no crash; unsupported characters become '?'