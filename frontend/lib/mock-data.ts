import type { AnalysisSummary, JobSummary } from "./types";

const daysAgo = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString();

export const MOCK_JOBS: JobSummary[] = [
  {
    id: "job-demo-1",
    title: "Backend Developer (Python)",
    created_at: daysAgo(12),
    required_skill_count: 5,
    preferred_skill_count: 4,
    analysis_count: 4,
  },
  {
    id: "job-demo-2",
    title: "Data Analyst",
    created_at: daysAgo(5),
    required_skill_count: 3,
    preferred_skill_count: 2,
    analysis_count: 1,
  },
];

export const MOCK_ANALYSES: AnalysisSummary[] = [
  { id: "a1", created_at: daysAgo(0), candidate_id: "c1", candidate_name: "Jane Example", job_id: "job-demo-1", job_title: "Backend Developer (Python)", score: 67, evidence_level: "moderate", ai_used: true },
  { id: "a2", created_at: daysAgo(1), candidate_id: "c2", candidate_name: "Sam Sample", job_id: "job-demo-1", job_title: "Backend Developer (Python)", score: 82, evidence_level: "strong", ai_used: true },
  { id: "a3", created_at: daysAgo(2), candidate_id: "c3", candidate_name: "Priya Placeholder", job_id: "job-demo-2", job_title: "Data Analyst", score: 44, evidence_level: "limited", ai_used: false },
  { id: "a4", created_at: daysAgo(4), candidate_id: "c4", candidate_name: "Alex Doe", job_id: "job-demo-1", job_title: "Backend Developer (Python)", score: 71, evidence_level: "moderate", ai_used: false },
  { id: "a5", created_at: daysAgo(6), candidate_id: "c1", candidate_name: "Jane Example", job_id: "job-demo-1", job_title: "Backend Developer (Python)", score: 58, evidence_level: "moderate", ai_used: true },
];