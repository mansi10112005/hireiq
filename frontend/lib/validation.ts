import type { WeightKey } from "./types";

export const MAX_UPLOAD_MB = 5; // same default as the backend
export const ALLOWED_EXTENSIONS = [".pdf", ".txt"];
export const JOB_MIN_CHARS = 30;
export const JOB_MAX_CHARS = 20_000;

export const DEFAULT_WEIGHTS: Record<WeightKey, string> = {
  required_skills: "50",
  preferred_skills: "15",
  experience: "20",
  projects_qualifications: "15",
};

export function validateFile(file: File | null): string | null {
  if (!file) return "Choose a resume file (PDF or TXT).";
  const name = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return "Unsupported file type. Please upload a PDF (.pdf) or text (.txt) resume.";
  }
  if (file.size === 0) return "The selected file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    return `The file is too large. The maximum size is ${MAX_UPLOAD_MB} MB.`;
  }
  return null;
}

/** Returns an error message, or null if the weights are valid. */
export function validateWeights(values: Record<WeightKey, string>): string | null {
  const numbers = Object.values(values).map((value) => Number(value));
  if (numbers.some((n) => value_is_bad(n))) {
    return "Each weight must be a number between 0 and 100.";
  }
  if (numbers.every((n) => n === 0)) {
    return "At least one weight must be greater than zero.";
  }
  return null;
}

function value_is_bad(n: number): boolean {
  return Number.isNaN(n) || n < 0 || n > 100;
}

export function toNumericWeights(values: Record<WeightKey, string>): Record<WeightKey, number> {
  return {
    required_skills: Number(values.required_skills),
    preferred_skills: Number(values.preferred_skills),
    experience: Number(values.experience),
    projects_qualifications: Number(values.projects_qualifications),
  };
}

/** Weights scaled to add up to 100 (like the backend does), or null if invalid. */
export function normalizedWeights(
  values: Record<WeightKey, string>,
): Record<WeightKey, number> | null {
  if (validateWeights(values)) return null;
  const numeric = toNumericWeights(values);
  const total = Object.values(numeric).reduce((sum, n) => sum + n, 0);
  return {
    required_skills: (numeric.required_skills / total) * 100,
    preferred_skills: (numeric.preferred_skills / total) * 100,
    experience: (numeric.experience / total) * 100,
    projects_qualifications: (numeric.projects_qualifications / total) * 100,
  };
}