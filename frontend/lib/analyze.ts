import { apiFetch } from "./api";
import type { AnalysisReport, AnalyzeInput, WeightKey } from "./types";
import { DEFAULT_WEIGHTS } from "./validation";

const TIMEOUT_MS = 5 * 60 * 1000; // AI analysis can take minutes on a free plan

/** Runs in the browser: uploads the resume and returns the full report. */
export async function submitAnalysis(input: AnalyzeInput): Promise<AnalysisReport> {
  const form = new FormData();
  form.append("file", input.file);

  if (input.jobMode === "saved") {
    form.append("job_id", input.jobId);
  } else {
    form.append("job_description", input.jobDescription);
    if (input.jobTitle.trim()) form.append("job_title", input.jobTitle.trim());
  }

  form.append("save_result", String(input.saveResult));
  form.append("enable_web_research", String(input.enableWebResearch));
  form.append("web_research_consent", String(input.webResearchConsent));

  // Only send weights when the user changed them, so the server's defaults apply otherwise.
  const keys = Object.keys(DEFAULT_WEIGHTS) as WeightKey[];
  const changed = keys.some((key) => input.weights[key] !== Number(DEFAULT_WEIGHTS[key]));
  if (changed) {
    for (const key of keys) form.append(`weight_${key}`, String(input.weights[key]));
  }

  // Note: we do NOT set a Content-Type header; the browser adds the multipart boundary itself.
  return apiFetch<AnalysisReport>("/analyses", {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
}