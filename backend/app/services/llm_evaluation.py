"""Node 6 (AI part): which experience/project entries relate to the job? Verified, then labelled."""

from app.schemas.analysis import EvaluationResult, RelevantEntry
from app.schemas.evidence import Evidence
from app.schemas.job import ParsedJobDescription
from app.schemas.llm import LLMEvaluation
from app.schemas.resume import ParsedResume
from app.services.evaluator import evaluate_candidate
from app.services.evidence_check import SourceText
from app.services.llm_client import StructuredLLM
from app.services.prompts import (
    EVALUATION_SYSTEM_PROMPT,
    format_job_requirements,
    format_resume_for_llm,
    wrap_untrusted,
)


def evaluate_with_llm(
    llm: StructuredLLM, resume: ParsedResume, job: ParsedJobDescription, text: str
) -> tuple[EvaluationResult, list[str]]:
    # The rule-based evaluation supplies the deterministic experience checks (and the fallback).
    base = evaluate_candidate(resume, job)

    user = (
        "Find the relevant entries.\n\n"
        + wrap_untrusted("candidate_data", format_resume_for_llm(resume))
        + "\n\n"
        + wrap_untrusted("job_requirements", format_job_requirements(job))
    )
    output = llm.generate(
        system=EVALUATION_SYSTEM_PROMPT,
        user=user,
        output_model=LLMEvaluation,
        schema_name="candidate_evaluation",
        max_output_tokens=2500,
    )

    source = SourceText(text)
    wanted = {
        skill.name.lower(): skill.name
        for skill in (*job.required_skills, *job.preferred_skills, *job.other_mentioned_skills)
    }

    entries: list[RelevantEntry] = []
    dropped = 0
    for item in output.relevant_entries[:10]:
        matched = [wanted[n.lower()] for n in item.matched_skills if n.lower() in wanted]
        if not (source.contains(item.heading) and source.contains(item.evidence_quote) and matched):
            dropped += 1
            continue
        entries.append(
            RelevantEntry(
                section=item.section,
                heading=" ".join(item.heading.split())[:200],
                matched_skills=list(dict.fromkeys(matched)),
                evidence=Evidence(
                    source="resume",
                    section=item.section,
                    snippet=" ".join(item.evidence_quote.split())[:200],
                ),
                explanation=" ".join(item.why_relevant.split())[:300],
            )
        )

    result = EvaluationResult(
        evaluator=f"ai:{llm.model_name}" if entries else base.evaluator,
        relevant_entries=entries or base.relevant_entries,
        experience_checks=base.experience_checks,
        notes=[*base.notes, *[f"(AI) {' '.join(n.split())[:200]}" for n in output.notes[:3]]],
    )

    notes: list[str] = []
    if dropped:
        notes.append(
            f"{dropped} AI evaluation items were discarded because their heading, quote or "
            "skills could not be verified."
        )
    return result, notes