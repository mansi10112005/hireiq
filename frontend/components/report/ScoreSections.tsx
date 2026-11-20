import { Card, CardHeader, ScoreBadge } from "@/components/ui/primitives";
import type { ScoreSection } from "@/lib/types";

const LEVEL_TEXT = {
  strong: "Most of the job's requirements are evidenced in the resume.",
  moderate: "Some of the job's requirements are evidenced in the resume.",
  limited: "Few of the job's requirements are evidenced in the resume.",
} as const;

export function ScoreCard({ score }: { score: ScoreSection }) {
  return (
    <Card>
      <CardHeader
        title="Match score"
        description="Calculated by transparent rules from evidence in the resume. No AI decides the score."
      />
      <div className="space-y-3 px-5 py-5">
        {score.status === "calculated" && score.value !== null ? (
          <>
            <div className="flex flex-wrap items-end gap-4">
              <p className="text-5xl font-semibold text-slate-900">
                {score.value}
                <span className="text-xl font-normal text-slate-600">/100</span>
              </p>
              <ScoreBadge score={score.value} level={score.evidence_level} />
            </div>
            {score.evidence_level && (
              <p className="text-sm text-slate-700">
                {LEVEL_TEXT[score.evidence_level]} These bands describe evidence coverage. They are
                not hire or reject decisions.
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-800">
            No score could be calculated for this job description. See the notes below.
          </p>
        )}
        <p className="text-sm text-slate-600">{score.disclaimer}</p>
      </div>
    </Card>
  );
}

export function ScoreBreakdown({ score }: { score: ScoreSection }) {
  return (
    <Card>
      <CardHeader
        title="Score breakdown"
        description="Each criterion earns a fraction from 0 to 1. Fraction × weight = points, and the points add up to the score."
      />
      <ul className="divide-y divide-slate-100">
        {score.components.map((component) => {
          const percent = component.fraction === null ? 0 : Math.round(component.fraction * 100);
          return (
            <li key={component.key} className="px-5 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-900">{component.label}</h3>
                <p className="text-sm text-slate-700">
                  {component.applicable
                    ? `${component.points.toFixed(1)} of ${component.effective_weight.toFixed(1)} points`
                    : "Not applicable"}
                </p>
              </div>

              {component.applicable ? (
                <div className="mt-2 flex items-center gap-3">
                  <div
                    className="h-2 flex-1 rounded-full bg-slate-100"
                    role="img"
                    aria-label={`${percent}% of this criterion is evidenced`}
                  >
                    <div className="h-2 rounded-full bg-indigo-600" style={{ width: `${percent}%` }} />
                  </div>
                  <span className="w-12 text-right text-sm text-slate-700">{percent}%</span>
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-600">
                  The job description gives no data for this criterion, so its weight was shared
                  among the others.
                </p>
              )}

              <p className="mt-1 text-xs text-slate-600">
                Configured weight {component.configured_weight.toFixed(0)}%
                {component.effective_weight !== component.configured_weight
                  ? `, used weight ${component.effective_weight.toFixed(1)}%`
                  : ""}
              </p>

              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-indigo-700">
                  How this was calculated
                </summary>
                <p className="mt-2 text-sm text-slate-700">{component.explanation}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {component.details.map((line, index) => (
                    <li key={index}>{line}</li>
                  ))}
                </ul>
              </details>
            </li>
          );
        })}
      </ul>
      <div className="space-y-2 border-t border-slate-100 px-5 py-4 text-sm text-slate-700">
        {score.notes.length > 0 && (
          <ul className="list-disc space-y-1 pl-5">
            {score.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        )}
        <p className="text-xs text-slate-600">
          Method: {score.method} · Partial credit for skills only listed in the Skills section:{" "}
          {score.partial_credit}
          {score.exact !== null ? ` · Unrounded score: ${score.exact}` : ""}
        </p>
      </div>
    </Card>
  );
}