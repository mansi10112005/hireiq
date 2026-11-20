"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { friendlyError } from "@/lib/errors";

type Target = "analysis" | "candidate";

interface DeleteRowProps {
  label: string;
  warning: string;
  confirming: boolean;
  busy: boolean;
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}

/** One delete action with a two-step confirmation. Defined outside the main component on purpose. */
function DeleteRow({ label, warning, confirming, busy, onAsk, onCancel, onConfirm }: DeleteRowProps) {
  if (!confirming) {
    return (
      <Button variant="secondary" onClick={onAsk}>
        {label}
      </Button>
    );
  }
  return (
    <div
      role="alert"
      className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900"
    >
      <p>{warning}</p>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={busy} onClick={onConfirm}>
          {busy ? "Deleting…" : "Yes, delete"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function DeleteButtons({
  analysisId,
  candidateId,
}: {
  analysisId: string;
  candidateId: string;
}) {
  const router = useRouter();
  const [confirming, setConfirming] = useState<Target | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove(target: Target) {
    setBusy(true);
    setError(null);
    try {
      const path = target === "analysis" ? `/analyses/${analysisId}` : `/candidates/${candidateId}`;
      await apiFetch<void>(path, { method: "DELETE" });
      router.push("/results");
    } catch (caught) {
      setError(friendlyError(caught));
      setBusy(false);
      setConfirming(null);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Privacy and data"
        description="You can remove stored data at any time. Deleting cannot be undone."
      />
      <div className="space-y-4 px-5 py-5">
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <DeleteRow
          label="Delete this analysis"
          warning="This deletes this report. If it is the candidate's only analysis, their record is deleted too."
          confirming={confirming === "analysis"}
          busy={busy}
          onAsk={() => setConfirming("analysis")}
          onCancel={() => setConfirming(null)}
          onConfirm={() => remove("analysis")}
        />
        <DeleteRow
          label="Delete this candidate and all their analyses"
          warning="This deletes the candidate's name, email and every saved analysis about them."
          confirming={confirming === "candidate"}
          busy={busy}
          onAsk={() => setConfirming("candidate")}
          onCancel={() => setConfirming(null)}
          onConfirm={() => remove("candidate")}
        />
      </div>
    </Card>
  );
}