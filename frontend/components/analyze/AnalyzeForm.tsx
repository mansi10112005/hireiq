"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { AlertIcon, Spinner } from "@/components/ui/icons";
import { Card, CardHeader } from "@/components/ui/primitives";
import { ReportView } from "@/components/report/ReportView";
import { submitAnalysis } from "@/lib/analyze";
import { friendlyError } from "@/lib/errors";
import type { AnalysisReport, JobMode, JobSummary, WeightKey } from "@/lib/types";
import {
  DEFAULT_WEIGHTS,
  JOB_MAX_CHARS,
  JOB_MIN_CHARS,
  toNumericWeights,
  validateFile,
  validateWeights,
} from "@/lib/validation";
import { FileDropzone } from "./FileDropzone";
import { WaitingPanel } from "./WaitingPanel";
import { WeightsEditor } from "./WeightsEditor";

type Status = "idle" | "running" | "done" | "error";

interface FormErrors {
  file?: string;
  job?: string;
  consent?: string;
  weights?: string;
}

const INPUT_CLASSES =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600";

export function AnalyzeForm({
  jobs,
  jobsUnavailable,
}: {
  jobs: JobSummary[];
  jobsUnavailable: string | null;
}) {
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [jobMode, setJobMode] = useState<JobMode>("paste");
  const [jobDescription, setJobDescription] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jobId, setJobId] = useState(jobs[0]?.id ?? "");
  const [saveResult, setSaveResult] = useState(true);
  const [enableWeb, setEnableWeb] = useState(false);
  const [consent, setConsent] = useState(false);
  const [weights, setWeights] = useState<Record<WeightKey, string>>({ ...DEFAULT_WEIGHTS });

  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<AnalysisReport | null>(null);
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
    setResult(null);

    try {
      const report = await submitAnalysis({
        file,
        jobMode,
        jobDescription,
        jobId,
        jobTitle,
        saveResult,
        enableWebResearch: enableWeb,
        webResearchConsent: consent,
        weights: toNumericWeights(weights),
      });

      if (report.storage.stored) {
        router.push(`/analyses/${report.analysis_id}`); // saved: open the permanent report page
        return;
      }
      setResult(report); // not saved: show it here, because it cannot be loaded again later
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
    setStatus("idle");
  }

  if (status === "done" && result) {
    return (
      <div className="space-y-6">
        <ReportView report={result} />
        <Button onClick={reset}>Analyze another resume</Button>
      </div>
    );
  }

  const errorList = Object.values(errors).filter(Boolean);

  return (
    <form onSubmit={handleSubmit} noValidate className="max-w-3xl space-y-6">
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
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900"
        >
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
            {jobsUnavailable && (
              <p role="note" className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Saved jobs are unavailable: {jobsUnavailable} You can still paste a job description.
              </p>
            )}

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
                    Headings such as &quot;Requirements&quot; and &quot;Nice to have&quot; help HireIQ
                    tell required skills from preferred ones.
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
                  Stores the parsed findings, name and email. Not stored: the original file, the full
                  resume text, phone number and links.
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
                    Kept separate from resume-based findings and clearly labelled. Real web research
                    is added in a later milestone; for now a demo adapter answers.
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
          </div>
        </Card>
      </fieldset>

      {running && <WaitingPanel />}

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