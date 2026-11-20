"use client";

import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/icons";
import { Card, CardHeader } from "@/components/ui/primitives";
import { PIPELINE_STEPS } from "@/lib/pipeline";

export function WaitingPanel() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((current) => current + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <Card>
      <CardHeader
        title="Analyzing…"
        description="The backend is working through the steps below. With AI enabled this can take up to a few minutes on a free plan."
      />
      <div className="space-y-4 px-5 py-5" role="status" aria-live="polite">
        <p className="flex items-center gap-2 text-sm font-medium text-slate-900">
          <Spinner className="h-4 w-4 text-indigo-600" />
          Working… {seconds}s elapsed
        </p>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
          {PIPELINE_STEPS.map((step) => (
            <li key={step.key}>{step.label}</li>
          ))}
        </ol>
        <p className="text-xs text-slate-600">
          Live per-step progress is not available yet. The finished report lists exactly which
          steps ran.
        </p>
      </div>
    </Card>
  );
}