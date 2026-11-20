/** An error with a machine-readable code, like the ones our backend returns. */
export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(code: string, message: string, status = 500, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  database_unavailable: "The database is not reachable. Check that MongoDB is running.",
  storage_disabled: "Storage is turned off on the server, so saved data is not available.",
  invalid_job_input: "Paste a job description or choose a saved job (not both).",
  invalid_scoring_weights: "At least one scoring weight must be greater than zero.",
  file_too_large: "That file is too large. Please upload a smaller resume.",
  unsupported_file_type: "Please upload a PDF (.pdf) or text (.txt) resume.",
  file_content_mismatch: "That file's contents do not match its extension. Please upload a real PDF or text file.",
  password_protected_pdf: "This PDF is password-protected. Please upload an unlocked copy.",
  ocr_required:
    "This PDF looks like a scanned image. Text recognition (OCR) is not supported yet, so please upload a text-based PDF or a .txt version.",
};

const FIELD_LABELS: Record<string, string> = {
  file: "Resume file",
  job_description: "Job description",
  job_id: "Saved job",
  job_title: "Job title",
  weight_required_skills: "Required-skills weight",
  weight_preferred_skills: "Preferred-skills weight",
  weight_experience: "Experience weight",
  weight_projects_qualifications: "Projects weight",
};

interface DetailItem {
  field: string;
  message: string;
}

function isDetailItem(value: unknown): value is DetailItem {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.field === "string" && typeof record.message === "string";
}

function describeDetails(details: unknown): string[] {
  if (!Array.isArray(details)) return [];
  return details.filter(isDetailItem).map((item) => {
    const key = item.field.split(".").pop() ?? item.field;
    return `${FIELD_LABELS[key] ?? key}: ${item.message}.`;
  });
}

/** Turns any error into a short message that is safe and helpful to show on screen. */
export function friendlyError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "validation_error") {
      const items = describeDetails(error.details);
      return items.length > 0 ? `${error.message} ${items.join(" ")}` : error.message;
    }
    return FRIENDLY_MESSAGES[error.code] ?? error.message;
  }
  return "Something went wrong on our side. Please try again.";
}