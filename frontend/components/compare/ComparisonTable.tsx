import Link from "next/link";
import { IMPORTANCE_LABEL, IMPORTANCE_TONE, type Tone } from "@/components/report/labels";
import { Badge, Card, CardHeader, ScoreBadge } from "@/components/ui/primitives";
import type { ComparisonResult, SkillStatus } from "@/lib/compare-types";
import { formatDate } from "@/lib/utils";

const STATUS_TEXT: Record<SkillStatus, string> = {
  supported: "Supported",
  partial: "Listed only",
  unverified: "No evidence found",
};

const STATUS_TONE: Record<SkillStatus, Tone> = {
  supported: "emerald",
  partial: "amber",
  unverified: "slate",
};

export function ComparisonTable({ result }: { result: ComparisonResult }) {
  const { candidates, skills, scoring } = result;
  const criteria = candidates[0]?.components ?? [];
  const weights = scoring.weights;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Scoring used for everyone"
          description="The same job requirements and the same weights were applied to every candidate."
        />
        <div className="space-y-2 px-5 py-4 text-sm text-slate-800">
          <p>
            Weights: required skills {weights.required_skills.toFixed(0)}% · preferred skills{" "}
            {weights.preferred_skills.toFixed(0)}% · experience {weights.experience.toFixed(0)}% ·
            projects and qualifications {weights.projects_qualifications.toFixed(0)}%. Partial
            credit: {scoring.partial_credit}.
          </p>
          <ul className="list-disc space-y-1 pl-5 text-slate-700">
            {result.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      </Card>

      <Card>
        <CardHeader
          title={`Side by side: ${result.job_title ?? "Untitled job"}`}
          description="Candidates appear in the order you selected. They are not ranked."
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <caption className="sr-only">
              Comparison of {candidates.length} candidates for {result.job_title ?? "the job"}
            </caption>
            <thead>
              <tr className="border-b border-slate-200">
                <td className="px-5 py-3" />
                {candidates.map((candidate) => (
                  <th key={candidate.analysis_id} scope="col" className="px-4 py-3 align-top font-medium">
                    <Link
                      href={`/analyses/${candidate.analysis_id}`}
                      className="text-indigo-700 hover:underline"
                    >
                      {candidate.candidate_name ?? "Unnamed candidate"}
                    </Link>
                    <span className="block text-xs font-normal text-slate-600">
                      {formatDate(candidate.analysed_at)}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <th scope="row" className="px-5 py-3 font-medium text-slate-900">
                  Match score
                </th>
                {candidates.map((candidate) => (
                  <td key={candidate.analysis_id} className="px-4 py-3 align-top">
                    <ScoreBadge score={candidate.score} level={candidate.evidence_level} />
                    {candidate.score_changed && (
                      <span className="mt-1 block text-xs text-amber-900">
                        Original report: {candidate.stored_score ?? "none"}
                      </span>
                    )}
                  </td>
                ))}
              </tr>

              {criteria.map((criterion, index) => (
                <tr key={criterion.key}>
                  <th scope="row" className="px-5 py-3 font-normal text-slate-700">
                    {criterion.label}
                  </th>
                  {candidates.map((candidate) => {
                    const component = candidate.components[index];
                    return (
                      <td key={candidate.analysis_id} className="px-4 py-3 text-slate-800">
                        {component.applicable && component.fraction !== null
                          ? `${Math.round(component.fraction * 100)}% evidenced`
                          : "Not applicable"}
                      </td>
                    );
                  })}
                </tr>
              ))}

              <tr>
                <th scope="row" className="px-5 py-3 font-normal text-slate-700">
                  Required skills shown in use
                </th>
                {candidates.map((candidate) => (
                  <td key={candidate.analysis_id} className="px-4 py-3 text-slate-800">
                    {candidate.required_supported} of {candidate.required_total}
                    {candidate.required_partial > 0 ? ` (+${candidate.required_partial} listed only)` : ""}
                  </td>
                ))}
              </tr>

              <tr className="bg-slate-50">
                <th scope="colgroup" colSpan={candidates.length + 1} className="px-5 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Skills
                </th>
              </tr>
              {skills.length === 0 && (
                <tr>
                  <td colSpan={candidates.length + 1} className="px-5 py-3 text-slate-700">
                    No skills were recognised in the job description.
                  </td>
                </tr>
              )}
              {skills.map((row) => (
                <tr key={row.name}>
                  <th scope="row" className="px-5 py-3 font-normal text-slate-900">
                    {row.name}{" "}
                    <Badge tone={IMPORTANCE_TONE[row.importance]}>{IMPORTANCE_LABEL[row.importance]}</Badge>
                  </th>
                  {row.statuses.map((status, index) => (
                    <td key={candidates[index].analysis_id} className="px-4 py-3">
                      <Badge tone={STATUS_TONE[status]}>{STATUS_TEXT[status]}</Badge>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="border-t border-slate-100 px-5 py-4 text-xs text-slate-600">{result.disclaimer}</p>
      </Card>
    </div>
  );
}