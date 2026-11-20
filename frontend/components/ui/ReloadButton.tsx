"use client";

import { useRouter } from "next/navigation";
import { Button } from "./Button";

/** Re-runs the current server page (used by error screens). */
export function ReloadButton({ label = "Try again" }: { label?: string }) {
  const router = useRouter();
  return (
    <Button variant="secondary" onClick={() => router.refresh()}>
      {label}
    </Button>
  );
}