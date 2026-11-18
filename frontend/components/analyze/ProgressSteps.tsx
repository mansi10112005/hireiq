import { CheckIcon, Spinner } from "@/components/ui/icons";
import { PIPELINE_STEPS } from "@/lib/pipeline";

export function ProgressSteps({
  currentStep,
  webEnabled,
}: {
  currentStep: number;
  webEnabled: boolean;
}) {
  return (
    <ol className="space-y-3" aria-label="Analysis progress">
      {PIPELINE_STEPS.map((step, index) => {
        const skipped = step.optional && !webEnabled;
        const done = !skipped && index < currentStep;
        const active = !skipped && index === currentStep;

        return (
          <li
            key={step.key}
            aria-current={active ? "step" : undefined}
            className="flex items-center gap-3 text-sm"
          >
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                done
                  ? "bg-emerald-600 text-white"
                  : active
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-300 text-slate-500"
              }`}
            >
              {done ? (
                <CheckIcon className="h-3.5 w-3.5" />
              ) : active ? (
                <Spinner className="h-3.5 w-3.5" />
              ) : (
                <span className="text-xs">{index + 1}</span>
              )}
            </span>
            <span
              className={
                skipped ? "text-slate-500 line-through" : active ? "font-medium text-slate-900" : "text-slate-700"
              }
            >
              {step.label}
            </span>
            {skipped && <span className="text-xs text-slate-600">(skipped)</span>}
          </li>
        );
      })}
    </ol>
  );
}