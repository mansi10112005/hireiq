import type { EvidenceLevel, Importance, ScoreComponent, ScoringWeights } from "./types";

export type SkillStatus = "supported" | "partial" | "unverified";

export interface ComparedCandidate {
  analysis_id: string;
  candidate_id: string | null;
  candidate_name: string | null;
  analysed_at: string;
  score: number | null;
  evidence_level: EvidenceLevel | null;
  stored_score: number | null;
  score_changed: boolean;
  components: ScoreComponent[];
  required_supported: number;
  required_partial: number;
  required_total: number;
}

export interface SkillComparisonRow {
  name: string;
  importance: Importance;
  statuses: SkillStatus[];
}

export interface ComparisonResult {
  job_id: string;
  job_title: string | null;
  scoring: {
    method: string;
    weights: ScoringWeights;
    partial_credit: number;
    entries_for_full_credit: number;
  };
  candidates: ComparedCandidate[];
  skills: SkillComparisonRow[];
  notes: string[];
  disclaimer: string;
}