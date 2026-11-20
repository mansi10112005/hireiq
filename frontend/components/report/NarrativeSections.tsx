import { Badge, Card, CardHeader } from "@/components/ui/primitives";
import type { CandidateSummary, EvaluationResult, SummaryStatement } from "@/lib/types";
import { EvidenceList } from "./Evidence";
import { ORIGIN_LABEL, ORIGIN_TONE } from "./labels";

function StatementList({ title, items }: { title: string; items: SummaryStatement[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <ul className="mt-2 space-y-3">
        {items.map((item, index) => (
          <li key={index}>
            <p className="text-sm text-slate-800">
              {item.text}{" "}
              <Badge tone={ORIGIN_TONE[item.origin]}>{ORIGIN_LABEL[item.origin]}</Badge>
            </p>
            {item.evidence.length > 0 && (
              <details className="mt-1">
                <summary className="cursor-pointer text-xs text-indigo-700">Show evidence</summary>
                <div className="mt-2">
                  <EvidenceList items={item.evidence} />
                </div>
              </details>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SummarySection({ summary }: { summary: CandidateSummary }) {
  const professional = summary.professional_summary ? [summary.professional_summary] : [];
  const empty =
    professional.length +
      summary.key_strengths.length +
      summary.experience_overview.length +
      summary.project_overview.length +
      summary.education_overview.length ===
    0;

  return (
    <Card>
      <CardHeader
        title="Candidate summary"
        description={
          summary.generator.startsWith("ai:")
            ? "Some statements were written by an AI model. Each one is labelled and has a supporting quote from the resume, but AI text can still be wrong. Please review it."
            : "Built from the resume with fixed templates. Every statement links to its evidence."
        }
      />
      <div className="space-y-6 px-5 py-5">
        {empty && (
          <p className="text-sm text-slate-700">
            Not enough structured information was found in the resume to summarize.
          </p>
        )}
        <StatementList title="Professional summary" items={professional} />
        <StatementList title="Key strengths (skills shown in use)" items={summary.key_strengths} />
        <StatementList title="Experience" items={summary.experience_overview} />
        <StatementList title="Projects" items={summary.project_overview} />
        <StatementList title="Education" items={summary.education_overview} />
      </div>
    </Card>
  );
}

const CHECK_TEXT = {
  meets_stated: "Meets the stated requirement",
  below_stated: "Below the stated requirement",
  unverified: "Could not be verified",
} as const;

export function EvaluationSection({ evaluation }: { evaluation: EvaluationResult }) {
  return (
    <Card>
      <CardHeader
        title="Relevant experience and projects"
        description={
          evaluation.evaluator.startsWith("ai:")
            ? "Explanations marked AI were written by a model; headings and quotes were checked against the resume."
            : "Entries that mention skills from the job description."
        }
      />
      <div className="space-y-6 px-5 py-5">
        {evaluation.relevant_entries.length === 0 ? (
          <p className="text-sm text-slate-700">
            No experience or project entries mention the job&apos;s skills in a way HireIQ could detect.
          </p>
        ) : (
          <ul className="space-y-4">
            {evaluation.relevant_entries.map((entry, index) => (
              <li key={index} className="rounded-lg border border-slate-200 p-3">
                <p className="text-sm font-medium text-slate-900">
                  {entry.heading} <Badge>{entry.section === "experience" ? "Experience" : "Project"}</Badge>
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {entry.matched_skills.map((skill) => (
                    <Badge key={skill} tone="indigo">
                      {skill}
                    </Badge>
                  ))}
                </div>
                {entry.explanation && (
                  <p className="mt-2 text-sm text-slate-700">
                    {entry.explanation} <Badge tone="indigo">AI explanation</Badge>
                  </p>
                )}
                <div className="mt-2">
                  <EvidenceList items={[entry.evidence]} />
                </div>
              </li>
            ))}
          </ul>
        )}

        {evaluation.experience_checks.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Years of experience</h3>
            <ul className="mt-2 space-y-2">
              {evaluation.experience_checks.map((check, index) => (
                <li key={index} className="text-sm text-slate-800">
                  <span className="font-medium">{CHECK_TEXT[check.status]}.</span> The job asks for
                  at least {check.min_years} years
                  {check.stated_years !== null ? `; the resume states ${check.stated_years}` : ""}.
                  <span className="block text-xs text-slate-600">{check.note}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evaluation.notes.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
            {evaluation.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

export function InterviewQuestions({ questions }: { questions: string[] }) {
  return (
    <Card>
      <CardHeader
        title="Suggested interview questions"
        description="Generated from skills that are only listed, or that have no evidence yet."
      />
      <div className="px-5 py-5">
        {questions.length === 0 ? (
          <p className="text-sm text-slate-700">No follow-up questions were suggested.</p>
        ) : (
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-800">
            {questions.map((question, index) => (
              <li key={index}>{question}</li>
            ))}
          </ol>
        )}
      </div>
    </Card>
  );
}