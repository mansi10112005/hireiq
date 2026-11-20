import { Badge, Card, CardHeader } from "@/components/ui/primitives";
import { PIPELINE_STEPS } from "@/lib/pipeline";
import type {
  AiUsage,
  JobSkill,
  ParsedJobDescription,
  WebIntelligenceResult,
} from "@/lib/types";

function SkillBadges({ title, skills }: { title: string; skills: JobSkill[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">{title}</h4>
      {skills.length === 0 ? (
        <p className="mt-1 text-sm text-slate-600">None.</p>
      ) : (
        <div className="mt-1 flex flex-wrap gap-1">
          {skills.map((skill) => (
            <Badge key={skill.name}>{skill.name}</Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export function JobRequirements({ job }: { job: ParsedJobDescription }) {
  return (
    <Card>
      <details>
        <summary className="cursor-pointer px-5 py-4 text-base font-semibold text-slate-900">
          Job requirements as understood by HireIQ
        </summary>
        <div className="space-y-4 border-t border-slate-100 px-5 py-5">
          <SkillBadges title="Required skills" skills={job.required_skills} />
          <SkillBadges title="Preferred skills" skills={job.preferred_skills} />
          <SkillBadges title="Mentioned (importance not stated)" skills={job.other_mentioned_skills} />
          {job.experience_requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                Experience requirements
              </h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-800">
                {job.experience_requirements.map((req, index) => (
                  <li key={index}>
                    {req.min_years}
                    {req.open_ended ? "+" : req.max_years ? `–${req.max_years}` : ""} years:
                    &ldquo;{req.evidence.snippet}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}
          {job.responsibilities.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                Responsibilities
              </h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-800">
                {job.responsibilities.map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-slate-600">Extracted by: {job.parser}</p>
        </div>
      </details>
    </Card>
  );
}

const WEB_STATUS_TEXT = {
  not_requested: "Not requested",
  skipped_no_consent: "Skipped: consent was not confirmed",
  mock: "Demo adapter: no real research was performed",
} as const;

export function ExternalResearch({ web }: { web: WebIntelligenceResult }) {
  return (
    <Card>
      <CardHeader
        title="External research"
        description="Information from public web sources. It is always kept separate from what the resume says, and it never changes the score."
      />
      <div className="space-y-2 px-5 py-5 text-sm text-slate-800">
        <p>
          <Badge tone={web.status === "mock" ? "amber" : "slate"}>{WEB_STATUS_TEXT[web.status]}</Badge>
        </p>
        <p>{web.note}</p>
        {web.findings.length > 0 && (
          <ul className="list-disc space-y-1 pl-5">
            {web.findings.map((finding, index) => (
              <li key={index}>{finding}</li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

function stepLabel(key: string): string {
  return PIPELINE_STEPS.find((step) => step.key === key)?.label ?? key;
}

export function AiAndPipeline({ ai, pipeline }: { ai: AiUsage; pipeline: string[] }) {
  return (
    <Card>
      <CardHeader title="How this report was produced" />
      <div className="space-y-4 px-5 py-5 text-sm text-slate-800">
        {ai.llm_configured ? (
          <div className="space-y-1">
            <p>
              AI model: <strong>{ai.model}</strong> ({ai.provider}). Steps that used AI:{" "}
              {ai.nodes_using_ai.length > 0 ? ai.nodes_using_ai.map(stepLabel).join(", ") : "none"}.
            </p>
            {ai.nodes_with_fallback.length > 0 && (
              <p className="text-amber-900">
                These steps could not use AI and fell back to rule-based results:{" "}
                {ai.nodes_with_fallback.map(stepLabel).join(", ")}.
              </p>
            )}
            <p className="text-xs text-slate-600">{ai.note}</p>
          </div>
        ) : (
          <p>AI was not used for this report. Everything came from rule-based parsing.</p>
        )}

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            Steps that ran
          </h3>
          <ol className="mt-2 space-y-1">
            {PIPELINE_STEPS.map((step) => {
              const ran = pipeline.includes(step.key);
              return (
                <li key={step.key} className="flex items-center gap-2">
                  <Badge tone={ran ? "emerald" : "slate"}>{ran ? "Done" : "Not run"}</Badge>
                  <span className={ran ? "text-slate-800" : "text-slate-500"}>{step.label}</span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </Card>
  );
}

export function Limitations({ items }: { items: string[] }) {
  return (
    <Card>
      <CardHeader
        title="Limitations — please read"
        description="Automated extraction and AI-written text require human validation. These safeguards reduce errors; they do not eliminate them."
      />
      <ul className="list-disc space-y-2 px-5 py-5 pl-10 text-sm text-slate-800">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </Card>
  );
}