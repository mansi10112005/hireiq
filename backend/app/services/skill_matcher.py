"""Node 7 logic: BASIC skill matching. Milestone 8 replaces it with weighted, validated scoring.

Rules:
  supported  = the skill appears in the resume outside the Skills list (shown in use)
  partial    = the skill is only listed in the Skills section
  unverified = no evidence found (this does NOT prove the candidate lacks the skill)
"""

from app.schemas.analysis import SkillMatch, SkillMatchResult
from app.schemas.job import ParsedJobDescription
from app.schemas.resume import ParsedResume


def match_skills(resume: ParsedResume, job: ParsedJobDescription) -> SkillMatchResult:
    resume_skills = {skill.name: skill for skill in resume.skills}
    matches: list[SkillMatch] = []

    for job_skill in (*job.required_skills, *job.preferred_skills, *job.other_mentioned_skills):
        skill = resume_skills.get(job_skill.name)
        if skill is None:
            status = "unverified"
            evidence = []
            note = (
                "No evidence of this skill was found in the resume. "
                "This does not prove the candidate lacks it."
            )
        else:
            outside = [e for e in skill.evidence if e.section != "skills"]
            if outside:
                status, evidence = "supported", outside
                note = "Appears in the resume outside the Skills list."
            else:
                status, evidence = "partial", skill.evidence
                note = "Listed in the Skills section only; not shown in experience or projects."

        matches.append(
            SkillMatch(
                name=job_skill.name,
                importance=job_skill.importance,
                status=status,
                evidence=evidence,
                requirement_evidence=job_skill.evidence,
                note=note,
            )
        )
    return SkillMatchResult(matches=matches)