"use client";

import { Button } from "@/components/ui/Button";
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
      title="Something went wrong"
      message={
        error.message ||
        "An unexpected problem occurred. Check that the backend is running and try again."
      }
      action={
        <Button variant="secondary" onClick={reset}>
          Try again
        </Button>
      }
    />
  );
}