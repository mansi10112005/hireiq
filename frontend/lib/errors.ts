/** An error with a machine-readable code, like the ones our backend returns. */
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status = 500) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  database_unavailable:
    "The database is not reachable. The analysis can still run, but it cannot be saved right now.",
  ai_provider_unavailable:
    "The AI provider is not available at the moment. Please try again in a minute.",
  file_too_large: "That file is too large. Please upload a smaller resume.",
  unsupported_file_type: "Please upload a PDF (.pdf) or text (.txt) resume.",
  ocr_required:
    "This PDF looks like a scanned image. Text recognition (OCR) is not supported yet, so please upload a text-based PDF or a .txt version.",
};

/** Turns any error into a short message that is safe and helpful to show on screen. */
export function friendlyError(error: unknown): string {
  if (error instanceof ApiError) {
    return FRIENDLY_MESSAGES[error.code] ?? error.message;
  }
  return "Something went wrong on our side. Please try again.";
}