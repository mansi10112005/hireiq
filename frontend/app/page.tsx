import Link from "next/link";
import { RecentAnalysesTable } from "@/components/dashboard/RecentAnalysesTable";
import { ButtonLink } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/primitives";
import { ReloadButton } from "@/components/ui/ReloadButton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { getAnalysisPage } from "@/lib/data";
import { friendlyError } from "@/lib/errors";
import type { AnalysisSummary, Page } from "@/lib/types";

const PAGE_SIZE = 10;

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: pageParam } = await searchParams;
  const page = Math.max(1, Number.parseInt(pageParam ?? "1", 10) || 1);

  let data: Page<AnalysisSummary>;
  try {
    data = await getAnalysisPage(page, PAGE_SIZE);
  } catch (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">Candidate results</h1>
        <ErrorState
          title="We couldn't load the results"
          message={friendlyError(error)}
          action={<ReloadButton />}
        />
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const linkClasses =
    "rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Candidate results</h1>
          <p className="mt-1 text-sm text-slate-600">
            All saved analyses, newest first. Scores are screening aids, not hiring decisions.
          </p>
        </div>
        <ButtonLink href="/analyze">Analyze a resume</ButtonLink>
      </div>

      <Card>
        <CardHeader title={`${data.total} saved ${data.total === 1 ? "analysis" : "analyses"}`} />
        {data.items.length === 0 ? (
          <EmptyState
            title="Nothing here yet"
            description="Saved analyses will appear in this list."
            action={<ButtonLink href="/analyze">Analyze a resume</ButtonLink>}
          />
        ) : (
          <RecentAnalysesTable items={data.items} />
        )}
      </Card>

      {totalPages > 1 && (
        <nav aria-label="Pagination" className="flex items-center justify-between">
          {page > 1 ? (
            <Link href={`/results?page=${page - 1}`} className={linkClasses}>
              ← Newer
            </Link>
          ) : (
            <span />
          )}
          <span className="text-sm text-slate-600">
            Page {page} of {totalPages}
          </span>
          {page < totalPages ? (
            <Link href={`/results?page=${page + 1}`} className={linkClasses}>
              Older →
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}
    </div>
  );
}