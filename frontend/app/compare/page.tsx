import type { Metadata } from "next";
import { ComparisonTable } from "@/components/compare/ComparisonTable";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card, CardHeader, ScoreBadge } from "@/components/ui/primitives";
import { EmptyState, ErrorState } from "@/components/ui/states";
import type { ComparisonResult } from "@/lib/compare-types";
import { getComparison, getJobAnalyses } from "@/lib/compare";
import { getSavedJobs } from "@/lib/data";
import { friendlyError } from "@/lib/errors";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = { title: "Compare Candidates — HireIQ" };

const MAX_COMPARED = 5;

const WEIGHT_FIELDS = [
  { key: "required_skills", label: "Required skills" },
  { key: "preferred_skills", label: "Preferred skills" },
  { key: "experience", label: "Experience" },
  { key: "projects_qualifications", label: "Projects and qualifications" },
] as const;

type SearchParams = { [key: string]: string | string[] | undefined };

function toArray(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

const INPUT_CLASSES =
  "mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600";

export default async function ComparePage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const jobId = toArray(params.job)[0] ?? "";
  const ids = toArray(params.ids);
  const weights: Record<string, string> = {};
  for (const field of WEIGHT_FIELDS) weights[field.key] = toArray(params[`weight_${field.key}`])[0] ?? "";

  const { jobs, unavailable } = await getSavedJobs();

  const heading = (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-900">Compare candidates</h1>
      <p className="mt-1 text-sm text-slate-600">
        Compare 2 to {MAX_COMPARED} candidates for the same job. Everyone is judged by the same
        requirements and the same weights. HireIQ does not rank or reject candidates.
      </p>
    </div>
  );

  if (unavailable) {
    return (
      <div className="space-y-6">
        {heading}
        <ErrorState title="Saved jobs could not be loaded" message={unavailable} />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="space-y-6">
        {heading}
        <Card>
          <EmptyState
            title="No saved jobs yet"
            description="Analyze at least two resumes against the same job description, then come back to compare them."
            action={<ButtonLink href="/analyze">Analyze a resume</ButtonLink>}
          />
        </Card>
      </div>
    );
  }

  // Step 2 data: the analyses for the chosen job
  let analyses: Awaited<ReturnType<typeof getJobAnalyses>> | null = null;
  let analysesError: string | null = null;
  if (jobId) {
    try {
      analyses = await getJobAnalyses(jobId);
    } catch (error) {
      analysesError = friendlyError(error);
    }
  }

  // Step 3 data: the comparison itself
  let comparison: ComparisonResult | null = null;
  let comparisonError: string | null = null;
  if (jobId && ids.length > 0) {
    if (ids.length < 2) {
      comparisonError = "Select at least two analyses to compare.";
    } else if (ids.length > MAX_COMPARED) {
      comparisonError = `You can compare at most ${MAX_COMPARED} analyses at once.`;
    } else {
      try {
        comparison = await getComparison(ids, weights);
      } catch (error) {
        comparisonError = friendlyError(error);
      }
    }
  }

  return (
    <div className="space-y-6">
      {heading}

      {/* Step 1: choose the job */}
      <Card>
        <CardHeader title="1. Choose a job" />
        <form method="get" className="flex flex-wrap items-end gap-3 px-5 py-5">
          <div>
            <label htmlFor="job" className="block text-sm font-medium text-slate-800">
              Saved job
            </label>
            <select id="job" name="job" defaultValue={jobId} className={`${INPUT_CLASSES} min-w-64`}>
              <option value="" disabled>
                Select a job…
              </option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {(job.title ?? "Untitled job") + ` (${job.analysis_count} analyses)`}
                </option>
              ))}
            </select>
          </div>
          <Button type="submit" variant="secondary">
            Show candidates
          </Button>
        </form>
      </Card>

      {/* Step 2: choose the candidates */}
      {jobId && (
        <Card>
          <CardHeader
            title={`2. Choose 2 to ${MAX_COMPARED} analyses`}
            description="Scores shown here come from each original report. The comparison recalculates them with one common weighting."
          />
          {analysesError ? (
            <p role="alert" className="px-5 py-4 text-sm text-red-700">
              {analysesError}
            </p>
          ) : analyses && analyses.items.length < 2 ? (
            <EmptyState
              title="Not enough analyses for this job"
              description="Analyze at least two resumes against this saved job, then come back."
              action={<ButtonLink href="/analyze">Analyze a resume</ButtonLink>}
            />
          ) : (
            analyses && (
              <form method="get" className="space-y-5 px-5 py-5">
                <input type="hidden" name="job" value={jobId} />
                <fieldset>
                  <legend className="sr-only">Analyses to compare</legend>
                  <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                    {analyses.items.map((item) => (
                      <li key={item.id}>
                        <label className="flex cursor-pointer flex-wrap items-center gap-3 px-4 py-3 text-sm">
                          <input type="checkbox" name="ids" value={item.id} defaultChecked={ids.includes(item.id)} />
                          <span className="font-medium text-slate-900">
                            {item.candidate_name ?? "Unnamed candidate"}
                          </span>
                          <span className="text-slate-600">{formatDate(item.created_at)}</span>
                          <ScoreBadge score={item.score} level={item.evidence_level} />
                        </label>
                      </li>
                    ))}
                  </ul>
                </fieldset>

                <details className="rounded-lg border border-slate-200">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">
                    Scoring weights for this comparison (optional)
                  </summary>
                  <div className="space-y-3 border-t border-slate-100 px-4 py-4">
                    <p className="text-sm text-slate-600">
                      Leave blank to use the defaults. Weights are relative and are scaled to add
                      up to 100%.
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {WEIGHT_FIELDS.map((field) => (
                        <div key={field.key}>
                          <label htmlFor={`weight_${field.key}`} className="block text-sm text-slate-800">
                            {field.label}
                          </label>
                          <input
                            id={`weight_${field.key}`}
                            name={`weight_${field.key}`}
                            type="number"
                            min={0}
                            max={100}
                            defaultValue={weights[field.key]}
                            className={`${INPUT_CLASSES} w-28`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </details>

                <Button type="submit">Compare selected</Button>
              </form>
            )
          )}
        </Card>
      )}

      {/* Step 3: the result */}
      {comparisonError && <ErrorState title="The comparison could not be made" message={comparisonError} />}
      {comparison && <ComparisonTable result={comparison} />}
    </div>
  );
}