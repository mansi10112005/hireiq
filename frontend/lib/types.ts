export type EvidenceLevel = "strong" | "moderate" | "limited";

export interface AnalysisSummary {
  id: string;
  created_at: string;
  candidate_id: string;
  candidate_name: string | null;
  job_id: string;
  job_title: string | null;
  score: number | null;
  evidence_level: EvidenceLevel | null;
  ai_used: boolean;
}

export interface JobSummary {
  id: string;
  title: string | null;
  created_at: string;
  required_skill_count: number;
  preferred_skill_count: number;
  analysis_count: number;
}

export interface DashboardData {
  totalCandidates: number;
  totalAnalyses: number;
  totalJobs: number;
  recent: AnalysisSummary[];
}

export type WeightKey =
  | "required_skills"
  | "preferred_skills"
  | "experience"
  | "projects_qualifications";

export type JobMode = "paste" | "saved";

/** What the form sends. */
export interface AnalyzeInput {
  file: File;
  jobMode: JobMode;
  jobDescription: string;
  jobId: string;
  jobTitle: string;
  saveResult: boolean;
  enableWebResearch: boolean;
  webResearchConsent: boolean;
  weights: Record<WeightKey, number>;
  simulateError: boolean; // demo only
}

/** A small part of the backend's AnalysisReport (the full report page comes in Milestone 11). */
export interface AnalysisPreview {
  analysis_id: string;
  candidate_name: string | null;
  score: number;
  evidence_level: EvidenceLevel;
  stored: boolean;
  warnings: string[];
}