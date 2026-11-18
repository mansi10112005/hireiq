export interface PipelineStep {
  key: string;
  label: string;
  optional?: boolean;
}

export const PIPELINE_STEPS: PipelineStep[] = [
  { key: "resume_upload", label: "Validating the resume" },
  { key: "text_extraction", label: "Extracting text" },
  { key: "cv_parsing", label: "Parsing the resume" },
  { key: "jd_skill_extraction", label: "Reading the job requirements" },
  { key: "candidate_summary", label: "Summarizing the candidate" },
  { key: "ai_evaluation", label: "Evaluating relevant experience" },
  { key: "skills_matching", label: "Matching skills and checking evidence" },
  { key: "web_intelligence", label: "Researching public sources (optional)", optional: true },
  { key: "score_and_store", label: "Calculating the score and saving" },
];