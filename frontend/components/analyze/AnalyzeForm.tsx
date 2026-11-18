"use client";

import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { AlertIcon, Spinner } from "@/components/ui/icons";
import { Card, CardHeader } from "@/components/ui/primitives";
import { submitAnalysis } from "@/lib/data";
import { friendlyError } from "@/lib/errors";
import type { AnalysisPreview, JobMode, JobSummary, WeightKey } from "@/lib/types";
import {
  DEFAULT_WEIGHTS,
  JOB_MAX_CHARS,
  JOB_MIN_CHARS,
  toNumericWeights,
  validateFile,
  validateWeights,
} from "@/lib/validation";
import { FileDropzone } from "./FileDropzone";
import { ProgressSteps } from "./ProgressSteps";
import { ResultPreview } from "./ResultPreview";
import { WeightsEditor } from "./WeightsEditor";

type Status = "idle" | "running" | "done" | "error";

interface FormErrors {
  file?: string;
  job?: string;
  consent?: string;
  weights?: string;
}

const SHOW_DEV_TOOLS = process.env.NODE_ENV !== "production";

const INPUT_CLASSES =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600";

export function AnalyzeForm({ jobs }: { jobs: JobSummary[] }) {
  const [file, setFile] = useState<File | null>(null);
  const [jobMode, setJobMode] = useState<JobMode>("paste");
  const [jobDescription, setJobDescription] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jobId, setJobId] = useState(jobs[0]?.id ?? "");
  const [saveResult, setSaveResult] = useState(true);
  const [enableWeb, setEnableWeb] = useState(false);
  const [consent, setConsent] = useState(false);
  const [weights, setWeights] = useState<Record<WeightKey, string>>({ ...DEFAULT_WEIGHTS });
  const [simulateError, setSimulateError] = useState(false);

  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<Status>("idle");
  const [step, setStep] = useState(-1);
  const [result, setResult] = useState<AnalysisPreview | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const summaryRef = useRef<HTMLDivElement>(null);

  const running = status === "running";
  const jobLength = jobDescription.trim().length;

  function validate(): FormErrors {
    const found: FormErrors = {};

    const fileError = validateFile(file);
    if (fileError) found.file = fileError;

    if (jobMode === "paste") {
      if (jobLength < JOB_MIN_CHARS) {
        found.job = `Paste at least ${JOB_MIN_CHARS} characters of the job description.`;
      } else if (jobLength > JOB_MAX_CHARS) {
        found.job = `The job description is too long (maximum ${JOB_MAX_CHARS} characters).`;
      }
    } else if (!jobId) {
      found.job = "Choose a saved job.";
    }

    if (enableWeb && !consent) {
      found.consent =
        "Confirm that you have the candidate's consent (or another lawful basis) before researching public web sources.";
    }

    const weightError = validateWeights(weights);
    if (weightError) found.weights = weightError;

    return found;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (running) return;

    const found = validate();
    setErrors(found);
    setServerError(null);

    if (Object.keys(found).length > 0 || !file) {
      setTimeout(() => summaryRef.current?.focus(), 0); // move focus to the error summary
      return;
    }

    setStatus("running");
    setStep(0);
    setResult(null);

    try {
      const preview = await submitAnalysis(
        {
          file,
          jobMode,
          jobDescription,
          jobId,
          jobTitle,
          saveResult,
          enableWebResearch: enableWeb,
          webResearchConsent: consent,
          weights: toNumericWeights(weights),
          simulateError,
        },
        setStep,
      );
      setResult(preview);
      setStatus("done");
    } catch (error) {
      setServerError(friendlyError(error));
      setStatus("error");
    }
  }

  function reset() {
    setFile(null);
    setJobDescription("");
    setJobTitle("");
    setSaveResult(true);
    setEnableWeb(false);
    setConsent(false);
    setWeights({ ...DEFAULT_WEIGHTS });
    setErrors({});
    setServerError(null);
    setResult(null);
    setStep(-1);
    setStatus("idle");
  }

  if (status === "done" && result) {
    return <ResultPreview result={result} onReset={reset} />;
  }

  const errorList = Object.values(errors).filter(Boolean);

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {errorList.length > 0 && (
        <div
          ref={summaryRef}
          tabIndex={-1}
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900 focus:outline-none"
        >
          <p className="font-medium">Please fix the following:</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {errorList.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      {serverError && (
        <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
          <div>
            <p className="font-medium">The analysis could not be completed</p>
            <p className="mt-1">{serverError}</p>
          </div>
        </div>
      )}

      <fieldset disabled={running} className="space-y-6">
        <Card>
          <CardHeader
            title="1. Resume"
            description="The file is analyzed in memory. The original resume file is never stored."
          />
          <div className="px-5 py-5">
            <FileDropzone file={file} error={errors.file} onChange={setFile} />
          </div>
        </Card>

        <Card>
          <CardHeader title="2. Job description" />
          <div className="space-y-4 px-5 py-5">
            <fieldset>
              <legend className="text-sm font-medium text-slate-800">Where does the job come from?</legend>
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-800">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="jobMode"
                    checked={jobMode === "paste"}
                    onChange={() => setJobMode("paste")}
                  />
                  Paste a job description
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="jobMode"
                    checked={jobMode === "saved"}
                    onChange={() => setJobMode("saved")}
                    disabled={jobs.length === 0}
                  />
                  Use a saved job
                </label>
              </div>
            </fieldset>

            {jobMode === "paste" ? (
              <>
                <div>
                  <label htmlFor="job-title" className="block text-sm font-medium text-slate-800">
                    Job title (optional)
                  </label>
                  <input
                    id="job-title"
                    type="text"
                    maxLength={200}
                    value={jobTitle}
                    onChange={(event) => setJobTitle(event.target.value)}
                    className={INPUT_CLASSES}
                  />
                </div>
                <div>
                  <label htmlFor="job-description" className="block text-sm font-medium text-slate-800">
                    Job description
                  </label>
                  <textarea
                    id="job-description"
                    rows={10}
                    value={jobDescription}
                    onChange={(event) => setJobDescription(event.target.value)}
                    aria-invalid={Boolean(errors.job)}
                    aria-describedby="job-description-count"
                    placeholder={"Backend Developer\n\nRequirements\n- Strong Python and SQL skills\n\nNice to have\n- Docker"}
                    className={INPUT_CLASSES}
                  />
                  <p id="job-description-count" className="mt-1 text-xs text-slate-600">
                    {jobLength.toLocaleString("en-US")} / {JOB_MAX_CHARS.toLocaleString("en-US")} characters.
                    Headings such as &quot;Requirements&quot; and &quot;Nice to have&quot; help HireIQ tell required skills from preferred ones.
                  </p>
                </div>
              </>
            ) : (
              <div>
                <label htmlFor="saved-job" className="block text-sm font-medium text-slate-800">
                  Saved job
                </label>
                <select
                  id="saved-job"
                  value={jobId}
                  onChange={(event) => setJobId(event.target.value)}
                  className={INPUT_CLASSES}
                >
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {(job.title ?? "Untitled job") +
                        ` (${job.required_skill_count} required, ${job.preferred_skill_count} preferred skills)`}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-slate-600">
                  A saved job uses the same requirements for every candidate, so scores are comparable.
                </p>
              </div>
            )}
            {errors.job && <p className="text-sm text-red-700">{errors.job}</p>}
          </div>
        </Card>

        <Card>
          <CardHeader title="3. Options" />
          <div className="space-y-4 px-5 py-5 text-sm text-slate-800">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={saveResult}
                onChange={(event) => setSaveResult(event.target.checked)}
              />
              <span>
                Save this analysis
                <span className="block text-xs text-slate-600">
                  Stores the parsed findings, name and email. Not stored: the original file, the
                  full resume text, phone number and links.
                </span>
              </span>
            </label>

            <div>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={enableWeb}
                  onChange={(event) => {
                    setEnableWeb(event.target.checked);
                    if (!event.target.checked) setConsent(false);
                  }}
                />
                <span>
                  Research public web sources (optional)
                  <span className="block text-xs text-slate-600">
                    Kept separate from resume-based findings and clearly labelled.
                  </span>
                </span>
              </label>

              {enableWeb && (
                <label className="ml-6 mt-3 flex items-start gap-2 rounded-lg bg-slate-50 p-3">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={consent}
                    onChange={(event) => setConsent(event.target.checked)}
                    aria-invalid={Boolean(errors.consent)}
                  />
                  <span>
                    I confirm I have the candidate&apos;s consent, or another lawful basis, to
                    research them online.
                  </span>
                </label>
              )}
            </div>

            <WeightsEditor
              values={weights}
              error={errors.weights}
              onChange={(key, value) => setWeights((current) => ({ ...current, [key]: value }))}
              onReset={() => setWeights({ ...DEFAULT_WEIGHTS })}
            />

            {SHOW_DEV_TOOLS && (
              <label className="flex items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={simulateError}
                  onChange={(event) => setSimulateError(event.target.checked)}
                />
                Developer tool: simulate a server error
              </label>
            )}
          </div>
        </Card>
      </fieldset>

      {running && (
        <Card>
          <CardHeader title="Analyzing…" description="This mirrors the nine steps of the backend workflow." />
          <div className="px-5 py-5" aria-live="polite">
            <ProgressSteps currentStep={step} webEnabled={enableWeb && consent} />
          </div>
        </Card>
      )}

      <div className="space-y-2">
        <Button type="submit" disabled={running}>
          {running && <Spinner className="h-4 w-4" />}
          {running ? "Analyzing…" : "Analyze resume"}
        </Button>
        <p className="text-xs text-slate-600">
          When AI is enabled on the server, text from the resume is sent to the AI provider (Groq)
          to help extract skills. Only use real candidate data if you have a lawful basis.
        </p>
      </div>
    </form>
  );
}