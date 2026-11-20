import { notFound } from "next/navigation";
import { ReportView } from "@/components/report/ReportView";
import { ReloadButton } from "@/components/ui/ReloadButton";
import { ErrorState } from "@/components/ui/states";
import { getAnalysis } from "@/lib/data";
import { ApiError, friendlyError } from "@/lib/errors";
import type { AnalysisReport } from "@/lib/types";

// In Next.js 16, params is a Promise, so we await it.
export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let report: AnalysisReport;
  try {
    report = await getAnalysis(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return (
      <ErrorState
        title="We couldn't load this report"
        message={friendlyError(error)}
        action={<ReloadButton />}
      />
    );
  }

  return <ReportView report={report} />;
}