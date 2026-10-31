"""Builds (wires together) the LangGraph workflow."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.workflows.nodes import (
    ai_evaluation_node,
    candidate_summary_node,
    cv_parsing_node,
    jd_skill_extraction_node,
    resume_upload_node,
    route_after_matching,
    score_and_store_node,
    skills_matching_node,
    text_extraction_node,
    web_intelligence_node,
)
from app.workflows.state import AnalysisState


def build_workflow():
    builder = StateGraph(AnalysisState)

    builder.add_node("resume_upload", resume_upload_node)
    builder.add_node("text_extraction", text_extraction_node)
    builder.add_node("cv_parsing", cv_parsing_node)
    builder.add_node("jd_skill_extraction", jd_skill_extraction_node)
    builder.add_node("candidate_summary", candidate_summary_node)
    builder.add_node("ai_evaluation", ai_evaluation_node)
    builder.add_node("skills_matching", skills_matching_node)
    builder.add_node("web_intelligence", web_intelligence_node)
    builder.add_node("score_and_store", score_and_store_node)

    builder.add_edge(START, "resume_upload")
    builder.add_edge("resume_upload", "text_extraction")
    builder.add_edge("text_extraction", "cv_parsing")
    builder.add_edge("cv_parsing", "jd_skill_extraction")
    builder.add_edge("jd_skill_extraction", "candidate_summary")
    builder.add_edge("candidate_summary", "ai_evaluation")
    builder.add_edge("ai_evaluation", "skills_matching")

    # Conditional edge: web research only when requested AND consented to
    builder.add_conditional_edges(
        "skills_matching",
        route_after_matching,
        {"web_intelligence": "web_intelligence", "score_and_store": "score_and_store"},
    )
    builder.add_edge("web_intelligence", "score_and_store")
    builder.add_edge("score_and_store", END)

    return builder.compile()


@lru_cache
def get_workflow():
    """Compile once and reuse (FastAPI dependency)."""
    return build_workflow()