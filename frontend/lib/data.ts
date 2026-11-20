import { apiFetch } from "./api";
import { friendlyError } from "./errors";
import type {
  AnalysisReport,
  AnalysisSummary,
  DashboardData,
  JobSummary,
  Page,
} from "./types";

/** Reads used by the server-rendered pages. */
export async function getDashboardData(): Promise<DashboardData> {
  const [analyses, candidates, jobs] = await Promise.all([
    apiFetch<Page<AnalysisSummary>>("/analyses?limit=5"),
    apiFetch<Page<unknown>>("/candidates?limit=1"),
    apiFetch<Page<unknown>>("/jobs?limit=1"),
  ]);
  return {
    totalCandidates: candidates.total,
    totalAnalyses: analyses.total,
    totalJobs: jobs.total,
    recent: analyses.items,
  };
}

export async function getAnalysisPage(page: number, pageSize: number): Promise<Page<AnalysisSummary>> {
  return apiFetch<Page<AnalysisSummary>>(`/analyses?limit=${pageSize}&skip=${(page - 1) * pageSize}`);
}

export async function getAnalysis(id: string): Promise<AnalysisReport> {
  return apiFetch<AnalysisReport>(`/analyses/${encodeURIComponent(id)}`);
}

/** Saved jobs are optional: if they cannot be loaded, the form still works with pasted text. */
export async function getSavedJobs(): Promise<{ jobs: JobSummary[]; unavailable: string | null }> {
  try {
    const page = await apiFetch<Page<JobSummary>>("/jobs?limit=100");
    return { jobs: page.items, unavailable: null };
  } catch (error) {
    return { jobs: [], unavailable: friendlyError(error) };
  }
}