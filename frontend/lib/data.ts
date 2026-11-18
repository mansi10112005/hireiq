import { ApiError } from "./errors";
import { MOCK_ANALYSES, MOCK_JOBS } from "./mock-data";
import { PIPELINE_STEPS } from "./pipeline";
import type { AnalysisPreview, AnalyzeInput, DashboardData, JobSummary } from "./types";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** `demo` comes from the page URL (?demo=empty | error | slow) to show each screen state. */
export async function getDashboardData(demo?: string): Promise<DashboardData> {
  await sleep(demo === "slow" ? 2500 : 300);

  if (demo === "error") {
    throw new ApiError("api_unreachable", "Could not reach the HireIQ API (demo error).", 503);
  }
  if (demo === "empty") {
    return { totalCandidates: 0, totalAnalyses: 0, totalJobs: 0, recent: [] };
  }
  return {
    totalCandidates: 4,
    totalAnalyses: MOCK_ANALYSES.length,
    totalJobs: MOCK_JOBS.length,
    recent: MOCK_ANALYSES,
  };
}

export async function getSavedJobs(): Promise<JobSummary[]> {
  await sleep(200);
  return MOCK_JOBS;
}

/** Pretends to run the nine workflow steps. `onStep` reports which step is running. */
export async function submitAnalysis(
  input: AnalyzeInput,
  onStep: (stepIndex: number) => void,
): Promise<AnalysisPreview> {
  const webAllowed = input.enableWebResearch && input.webResearchConsent;

  for (let index = 0; index < PIPELINE_STEPS.length; index++) {
    const step = PIPELINE_STEPS[index];
    if (step.optional && !webAllowed) continue; // skipped, like the backend's conditional edge
    onStep(index);
    await sleep(450);
    if (input.simulateError && step.key === "ai_evaluation") {
      throw new ApiError("ai_provider_unavailable", "The AI provider is unavailable.", 503);
    }
  }

  return {
    analysis_id: "demo-analysis",
    candidate_name: "Demo Candidate",
    score: 67,
    evidence_level: "moderate",
    stored: input.saveResult,
    warnings: ["Demo result: no real analysis was run, and this score is not based on your resume."],
  };
}