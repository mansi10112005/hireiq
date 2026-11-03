"""Node 5 (AI part): short AI-written statements, each backed by a VERIFIED quote."""

from app.schemas.analysis import CandidateSummary, SummaryStatement
from app.schemas.evidence import Evidence
from app.schemas.llm import LLMStatement, LLMSummary
from app.schemas.resume import ParsedResume
from app.services.evidence_check import SourceText
from app.services.llm_client import StructuredLLM
from app.services.llm_resume import resume_sections
from app.services.prompts import SUMMARY_SYSTEM_PROMPT, format_resume_for_llm, wrap_untrusted
from app.services.summary_builder import build_candidate_summary


def summarize_with_llm(
    llm: StructuredLLM, resume: ParsedResume, text: str
) -> tuple[CandidateSummary, list[str]]:
    template = build_candidate_summary(resume)  # used wherever the AI gives nothing verifiable
    user = "Write the statements from this candidate data.\n\n" + wrap_untrusted(
        "candidate_data", format_resume_for_llm(resume)
    )
    output = llm.generate(
        system=SUMMARY_SYSTEM_PROMPT,
        user=user,
        output_model=LLMSummary,
        schema_name="candidate_summary",
        max_output_tokens=2000,
    )

    source = SourceText(text, resume_sections(text))
    dropped = 0

    def convert(item: LLMStatement | None) -> SummaryStatement | None:
        nonlocal dropped
        if item is None:
            return None
        statement = " ".join(item.text.split())
        if not statement or not source.contains(item.evidence_quote):
            dropped += 1
            return None
        quote = " ".join(item.evidence_quote.split())[:200]
        return SummaryStatement(
            text=statement[:300],
            origin="ai",
            evidence=[
                Evidence(source="resume", section=source.section_of(quote), snippet=quote)
            ],
        )

    def convert_list(items: list[LLMStatement]) -> list[SummaryStatement]:
        return [s for s in (convert(item) for item in items[:6]) if s is not None]

    summary = CandidateSummary(
        professional_summary=convert(output.professional_summary) or template.professional_summary,
        experience_overview=convert_list(output.experience_highlights)
        or template.experience_overview,
        education_overview=template.education_overview,
        project_overview=convert_list(output.project_highlights) or template.project_overview,
        key_strengths=convert_list(output.key_strengths) or template.key_strengths,
    )
    uses_ai = any(
        statement.origin == "ai"
        for statement in (
            [summary.professional_summary] if summary.professional_summary else []
        )
        + summary.experience_overview
        + summary.project_overview
        + summary.key_strengths
    )
    summary.generator = f"ai:{llm.model_name}" if uses_ai else "template_v0"

    notes: list[str] = []
    if dropped:
        notes.append(
            f"{dropped} AI-written summary statements were discarded because their supporting "
            "quote could not be found in the resume."
        )
    return summary, notes