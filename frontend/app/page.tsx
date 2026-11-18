import { DemoStates } from "@/components/dashboard/DemoStates";
import { RecentAnalysesTable } from "@/components/dashboard/RecentAnalysesTable";
import { ButtonLink } from "@/components/ui/Button";
import { Card, CardHeader, StatCard } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/states";
import { getDashboardData } from "@/lib/data";

// In Next.js 16, searchParams is a Promise, so we await it.
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ demo?: string }>;
}) {
  const { demo } = await searchParams;
  const data = await getDashboardData(demo);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Evidence-based candidate analysis, with every finding traceable to the resume.
          </p>
        </div>
        <ButtonLink href="/analyze">Analyze a resume</ButtonLink>
      </div>

      <div
        role="note"
        className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      >
        You are looking at <strong>demo data</strong>. The connection to your real backend is built
        in Milestone 11.
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Candidates analyzed" value={data.totalCandidates} />
        <StatCard label="Analyses saved" value={data.totalAnalyses} />
        <StatCard label="Saved jobs" value={data.totalJobs} />
        <StatCard label="Data source" value="Demo" hint="Live API in Milestone 11" />
      </div>

      <Card>
        <CardHeader
          title="Recent evaluations"
          description="Scores describe how much of the job's requirements the resume evidences. They are a screening aid, not a hiring decision."
        />
        {data.recent.length === 0 ? (
          <EmptyState
            title="No analyses yet"
            description="Upload a resume and a job description to create your first evaluation."
            action={<ButtonLink href="/analyze">Analyze a resume</ButtonLink>}
          />
        ) : (
          <RecentAnalysesTable items={data.recent} />
        )}
      </Card>

      <DemoStates />
    </div>
  );
}