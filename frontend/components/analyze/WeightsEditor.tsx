"use client";

import { Button } from "@/components/ui/Button";
import type { WeightKey } from "@/lib/types";
import { normalizedWeights } from "@/lib/validation";

const FIELDS: { key: WeightKey; label: string; hint: string }[] = [
  { key: "required_skills", label: "Required skills", hint: "Skills the job says are required" },
  { key: "preferred_skills", label: "Preferred skills", hint: "Nice-to-have skills" },
  { key: "experience", label: "Relevant experience", hint: "Experience entries that match the job" },
  { key: "projects_qualifications", label: "Projects and qualifications", hint: "Relevant projects and certifications" },
];

interface WeightsEditorProps {
  values: Record<WeightKey, string>;
  error?: string;
  onChange: (key: WeightKey, value: string) => void;
  onReset: () => void;
}

export function WeightsEditor({ values, error, onChange, onReset }: WeightsEditorProps) {
  const normalized = normalizedWeights(values);

  return (
    <details className="rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer select-none rounded-lg px-4 py-3 text-sm font-medium text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600">
        Scoring weights (optional)
      </summary>
      <div className="space-y-4 border-t border-slate-100 px-4 py-4">
        <p className="text-sm text-slate-600">
          Weights are relative: they are scaled to add up to 100%. Use the same weights for every
          candidate you compare for one job.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          {FIELDS.map((field) => (
            <div key={field.key}>
              <label htmlFor={`weight-${field.key}`} className="block text-sm font-medium text-slate-800">
                {field.label}
              </label>
              <p id={`weight-${field.key}-hint`} className="text-xs text-slate-600">
                {field.hint}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <input
                  id={`weight-${field.key}`}
                  type="number"
                  min={0}
                  max={100}
                  inputMode="numeric"
                  value={values[field.key]}
                  onChange={(event) => onChange(field.key, event.target.value)}
                  aria-describedby={`weight-${field.key}-hint`}
                  className="w-24 rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
                />
                <span className="text-sm text-slate-600">
                  {normalized ? `= ${normalized[field.key].toFixed(0)}% of the score` : "—"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {error && <p className="text-sm text-red-700">{error}</p>}

        <Button type="button" variant="secondary" onClick={onReset}>
          Reset to defaults
        </Button>
      </div>
    </details>
  );
}