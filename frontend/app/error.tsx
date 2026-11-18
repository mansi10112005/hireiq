"use client";

import { ErrorState } from "@/components/ui/states";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorState
      title="We couldn't load this page"
      message={
        error.message ||
        "The server could not be reached. Check that the backend is running and try again."
      }
      onRetry={reset}
    />
  );
}