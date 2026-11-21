import { apiFetch } from "./api";
import type { ComparisonResult } from "./compare-types";
import type { AnalysisSummary, Page } from "./types";

export async function getJobAnalyses(jobId: string): Promise<Page<AnalysisSummary>> {
  return apiFetch<Page<AnalysisSummary>>(
    `/analyses?job_id=${encodeURIComponent(jobId)}&limit=100`,
  );
}

/** `weights` values may be empty strings; empty ones are left out so the server defaults apply. */
export async function getComparison(
  ids: string[],
  weights: Record<string, string>,
): Promise<ComparisonResult> {
  const query = new URLSearchParams();
  for (const id of ids) query.append("analysis_ids", id);
  for (const [key, value] of Object.entries(weights)) {
    if (value.trim() !== "") query.append(`weight_${key}`, value.trim());
  }
  return apiFetch<ComparisonResult>(`/comparisons?${query.toString()}`);
}