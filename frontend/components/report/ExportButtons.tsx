"use client";

import { Button } from "@/components/ui/Button";
import { API_URL } from "@/lib/api";
import type { AnalysisReport } from "@/lib/types";

const LINK_CLASSES =
  "inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2";

/** Saved reports: download from the server (PDF or JSON). Unsaved reports: JSON from the browser. */
export function ExportButtons({ report }: { report: AnalysisReport }) {
  if (report.storage.stored) {
    const base = `${API_URL}/api/v1/analyses/${report.analysis_id}/export`;
    return (
      <div className="flex flex-wrap gap-2">
        <a href={`${base}?format=pdf`} className={LINK_CLASSES}>
          Download PDF
        </a>
        <a href={`${base}?format=json`} className={LINK_CLASSES}>
          Download JSON
        </a>
      </div>
    );
  }

  function downloadJson() {
    const payload = {
      format: "hireiq-report/1",
      exported_at: new Date().toISOString(),
      report,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `hireiq-report-${report.analysis_id.slice(0, 8)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Button variant="secondary" onClick={downloadJson}>
      Download JSON
    </Button>
  );
}