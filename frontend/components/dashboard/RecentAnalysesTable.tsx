import { Badge, ScoreBadge } from "@/components/ui/primitives";
import { formatDate } from "@/lib/utils";
import type { AnalysisSummary } from "@/lib/types";

export function RecentAnalysesTable({ items }: { items: AnalysisSummary[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <caption className="sr-only">Recent candidate evaluations</caption>
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th scope="col" className="px-5 py-3 font-medium">Candidate</th>
            <th scope="col" className="px-5 py-3 font-medium">Job</th>
            <th scope="col" className="px-5 py-3 font-medium">Match score</th>
            <th scope="col" className="px-5 py-3 font-medium">Method</th>
            <th scope="col" className="px-5 py-3 font-medium">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => (
            <tr key={item.id}>
              <th scope="row" className="px-5 py-3 font-medium text-slate-900">
                {item.candidate_name ?? "Unnamed candidate"}
              </th>
              <td className="px-5 py-3 text-slate-700">{item.job_title ?? "Untitled job"}</td>
              <td className="px-5 py-3">
                <ScoreBadge score={item.score} level={item.evidence_level} />
              </td>
              <td className="px-5 py-3">
                <Badge tone={item.ai_used ? "indigo" : "slate"}>
                  {item.ai_used ? "AI-assisted" : "Rule-based"}
                </Badge>
              </td>
              <td className="px-5 py-3 text-slate-600">{formatDate(item.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}