import type { Metadata } from "next";
import { AnalyzeForm } from "@/components/analyze/AnalyzeForm";
import { getSavedJobs } from "@/lib/data";

export const metadata: Metadata = { title: "Analyze Resume — HireIQ" };

export default async function AnalyzePage() {
  const { jobs, unavailable } = await getSavedJobs();

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold text-slate-900">Analyze a resume</h1>
        <p className="mt-1 text-sm text-slate-600">
          Compare one resume with a job description. Every finding is backed by evidence from the
          text, and the match score is calculated by transparent rules, not by an AI.
        </p>
      </div>
      <AnalyzeForm jobs={jobs} jobsUnavailable={unavailable} />
    </div>
  );
}