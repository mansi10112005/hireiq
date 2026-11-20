import Link from "next/link";
import { Badge } from "@/components/ui/primitives";
import type { AnalysisReport } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { DeleteButtons } from "./DeleteButtons";
import { EvaluationSection, InterviewQuestions, SummarySection } from "./NarrativeSections";
import { AiAndPipeline, ExternalResearch, JobRequirements, Limitations } from "./MetaSections";
import { ScoreBreakdown, ScoreCard } from "./ScoreSections";
import { SkillsSection } from "./SkillsSection";

export function ReportView({ report }: { report: AnalysisReport }) {
  const saved = report.storage.stored;
  const usedAi = report.ai_usage.nodes_using_ai.length > 0;

  return (
    <div className="space-y-6">
      <Link href="/results" className="text-sm text-indigo-700 hover:underline">
        ← All results
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-600">Candidate report</p>
          <h1 className="text-2xl font-semibold text-slate-900">
            {report.candidate_name ?? "Unnamed candidate"}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {report.job_title ?? "Untitled job"} · {formatDateTime(report.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={saved ? "emerald" : "amber"}>{saved ? "Saved" : "Not saved"}</Badge>
          <Badge tone={usedAi ? "indigo" : "slate"}>{usedAi ? "AI-assisted" : "Rule-based"}</Badge>
        </div>
      </header>

      {!saved && (
        <div role="note" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This report was <strong>not saved</strong>, so it will disappear when you leave this page.{" "}
          {report.storage.note}
        </div>
      )}

      {report.warnings.length > 0 && (
        <section aria-label="Warnings" className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="text-sm font-semibold text-amber-900">Warnings</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {report.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </section>
      )}

      <ScoreCard score={report.score} />
      <ScoreBreakdown score={report.score} />
      <SkillsSection result={report.skill_matches} />
      <SummarySection summary={report.summary} />
      <EvaluationSection evaluation={report.evaluation} />
      <InterviewQuestions questions={report.interview_questions} />
      <JobRequirements job={report.job} />
      <ExternalResearch web={report.web_intelligence} />
      <AiAndPipeline ai={report.ai_usage} pipeline={report.pipeline} />
      <Limitations items={report.limitations} />

      {saved && report.storage.candidate_id && (
        <DeleteButtons analysisId={report.analysis_id} candidateId={report.storage.candidate_id} />
      )}
    </div>
  );
}