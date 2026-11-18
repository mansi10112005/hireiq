import { Button, ButtonLink } from "@/components/ui/Button";
import { CheckIcon } from "@/components/ui/icons";
import { Badge, Card, CardHeader, ScoreBadge } from "@/components/ui/primitives";
import type { AnalysisPreview } from "@/lib/types";

export function ResultPreview({
  result,
  onReset,
}: {
  result: AnalysisPreview;
  onReset: () => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Analysis complete"
        description="This is a short preview. The full evidence-backed report page is built in Milestone 11."
        action={<Badge tone="amber">Demo result</Badge>}
      />
      <div className="space-y-5 px-5 py-5" role="status">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-white">
            <CheckIcon className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm text-slate-600">{result.candidate_name ?? "Unnamed candidate"}</p>
            <ScoreBadge score={result.score} level={result.evidence_level} />
          </div>
        </div>

        <p className="text-sm text-slate-700">
          {result.stored
            ? "This analysis was saved. The original resume file is never stored."
            : "This analysis was not saved."}
        </p>

        {result.warnings.length > 0 && (
          <ul className="list-disc space-y-1 rounded-lg bg-amber-50 py-3 pl-8 pr-4 text-sm text-amber-900">
            {result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        )}

        <div className="flex flex-wrap gap-3">
          <Button onClick={onReset}>Analyze another resume</Button>
          <ButtonLink href="/" variant="secondary">
            Back to dashboard
          </ButtonLink>
        </div>
      </div>
    </Card>
  );
}