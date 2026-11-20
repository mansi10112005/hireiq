export type EvidenceLevel = "strong" | "moderate" | "limited";

export type WeightKey =
  | "required_skills"
  | "preferred_skills"
  | "experience"
  | "projects_qualifications";

export type JobMode = "paste" | "saved";

// ---------- Pages and lists ----------
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  skip: number;
}

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

// ---------- The full report (mirrors the backend's AnalysisReport) ----------
export interface Evidence {
  source: "resume" | "job_description";
  section: string | null;
  snippet: string;
}

export interface ContactInfo {
  name: string | null;
  email: string | null;
  phone: string | null;
  github_url: string | null;
  linkedin_url: string | null;
}

export interface ResumeEntry {
  heading: string;
  details: string[];
  date_range: string | null;
}

export interface ResumeSkill {
  name: string;
  in_skills_section: boolean;
  evidence: Evidence[];
}

export interface ExperienceStatement {
  years: number;
  evidence: Evidence;
}

export interface ParsedResume {
  parser: string;
  contact: ContactInfo;
  summary: string | null;
  education: ResumeEntry[];
  experience: ResumeEntry[];
  projects: ResumeEntry[];
  skills: ResumeSkill[];
  other_listed_skills: string[];
  certifications: string[];
  stated_years_of_experience: ExperienceStatement | null;
  sections_found: string[];
  missing_fields: string[];
  warnings: string[];
}

export type Importance = "required" | "preferred" | "unspecified";

export interface JobSkill {
  name: string;
  importance: Importance;
  evidence: Evidence[];
}

export interface ExperienceRequirement {
  min_years: number;
  max_years: number | null;
  open_ended: boolean;
  evidence: Evidence;
}

export interface ParsedJobDescription {
  parser: string;
  title: string | null;
  required_skills: JobSkill[];
  preferred_skills: JobSkill[];
  other_mentioned_skills: JobSkill[];
  responsibilities: string[];
  experience_requirements: ExperienceRequirement[];
  sections_found: string[];
  warnings: string[];
}

export type Origin = "resume" | "derived" | "ai";

export interface SummaryStatement {
  text: string;
  origin: Origin;
  evidence: Evidence[];
}

export interface CandidateSummary {
  generator: string;
  professional_summary: SummaryStatement | null;
  experience_overview: SummaryStatement[];
  education_overview: SummaryStatement[];
  project_overview: SummaryStatement[];
  key_strengths: SummaryStatement[];
}

export interface RelevantEntry {
  section: "experience" | "projects";
  heading: string;
  matched_skills: string[];
  evidence: Evidence;
  explanation: string | null;
}

export interface ExperienceCheck {
  requirement: string;
  min_years: number;
  stated_years: number | null;
  status: "meets_stated" | "below_stated" | "unverified";
  note: string;
}

export interface EvaluationResult {
  evaluator: string;
  relevant_entries: RelevantEntry[];
  experience_checks: ExperienceCheck[];
  notes: string[];
}

export interface SkillMatch {
  name: string;
  importance: Importance;
  status: "supported" | "partial" | "unverified";
  evidence: Evidence[];
  requirement_evidence: Evidence[];
  note: string;
}

export interface SkillMatchResult {
  method: string;
  matches: SkillMatch[];
  validation: { checked: number; rejected: number };
}

export interface WebIntelligenceResult {
  status: "not_requested" | "skipped_no_consent" | "mock";
  note: string;
  findings: string[];
}

export interface AiUsage {
  llm_configured: boolean;
  provider: string | null;
  model: string | null;
  nodes_using_ai: string[];
  nodes_with_fallback: string[];
  note: string;
}

export interface ScoringWeights {
  required_skills: number;
  preferred_skills: number;
  experience: number;
  projects_qualifications: number;
}

export interface ScoreComponent {
  key: WeightKey;
  label: string;
  applicable: boolean;
  fraction: number | null;
  configured_weight: number;
  effective_weight: number;
  points: number;
  explanation: string;
  details: string[];
}

export interface ScoreSection {
  status: "calculated" | "not_calculated";
  value: number | null;
  exact: number | null;
  evidence_level: EvidenceLevel | null;
  method: string;
  weights: ScoringWeights;
  partial_credit: number;
  entries_for_full_credit: number;
  components: ScoreComponent[];
  notes: string[];
  disclaimer: string;
}

export interface StorageSection {
  stored: boolean;
  candidate_id: string | null;
  job_id: string | null;
  note: string;
}

export interface AnalysisReport {
  analysis_id: string;
  created_at: string;
  workflow_version: string;
  job_title: string | null;
  candidate_name: string | null;
  resume: ParsedResume;
  job: ParsedJobDescription;
  summary: CandidateSummary;
  evaluation: EvaluationResult;
  skill_matches: SkillMatchResult;
  unverified_required_skills: string[];
  interview_questions: string[];
  score: ScoreSection;
  web_intelligence: WebIntelligenceResult;
  ai_usage: AiUsage;
  storage: StorageSection;
  warnings: string[];
  limitations: string[];
  pipeline: string[];
}

// ---------- What the analyze form sends ----------
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
}