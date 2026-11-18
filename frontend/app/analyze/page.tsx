import type { Metadata } from "next";
import { AnalyzeForm } from "@/components/analyze/AnalyzeForm";
import { getSavedJobs } from "@/lib/data";

export const metadata: Metadata = { title: "Analyze Resume — HireIQ" };

export default async function AnalyzePage() {
  const jobs = await getSavedJobs();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Analyze a resume</h1>
        <p className="mt-1 text-sm text-slate-600">
          Compare one resume with a job description. Every finding is backed by evidence from the
          text, and the match score is calculated by transparent rules, not by an AI.
        </p>
      </div>
      <div
        role="note"
        className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        This form runs on <strong>demo data</strong> for now. Nothing is sent to your backend until
        Milestone 11.
      </div>
      <AnalyzeForm jobs={jobs} />
    </div>
  );
}