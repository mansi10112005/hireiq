import { ApiError } from "./errors";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/**
 * The ONE place that talks to the backend. Works on the server and in the browser.
 * Turns the backend's error format into a typed ApiError.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, { cache: "no-store", ...init });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError("timeout", "The analysis took too long and was stopped. Please try again.", 0);
    }
    throw new ApiError(
      "network_error",
      "Could not reach the HireIQ backend. Check that it is running.",
      0,
    );
  }

  if (!response.ok) {
    let code = "http_error";
    let message = `The server returned an error (HTTP ${response.status}).`;
    let details: unknown = null;
    try {
      const body = await response.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        details = body.error.details ?? null;
      }
    } catch {
      // The response was not JSON; keep the generic message.
    }
    throw new ApiError(code, message, response.status, details);
  }

  if (response.status === 204) return undefined as T; // e.g. after DELETE
  return (await response.json()) as T;
}