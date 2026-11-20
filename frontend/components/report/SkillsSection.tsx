import { Badge, Card, CardHeader } from "@/components/ui/primitives";
import type { SkillMatch, SkillMatchResult } from "@/lib/types";
import { EvidenceList } from "./Evidence";
import { IMPORTANCE_LABEL, IMPORTANCE_TONE, type Tone } from "./labels";

const GROUPS: { status: SkillMatch["status"]; title: string; description: string; tone: Tone }[] = [
  {
    status: "supported",
    title: "Supported",
    description: "Shown in use in the resume, for example in experience or projects.",
    tone: "emerald",
  },
  {
    status: "partial",
    title: "Partially supported",
    description: "Only listed in the Skills section; not shown in use.",
    tone: "amber",
  },
  {
    status: "unverified",
    title: "Unverified (no evidence found)",
    description:
      "The resume gives no evidence of these skills. This does not prove the candidate lacks them.",
    tone: "slate",
  },
];

export function SkillsSection({ result }: { result: SkillMatchResult }) {
  return (
    <Card>
      <CardHeader
        title="Skills and evidence"
        description="Open a skill to see the exact lines of text behind the finding."
      />
      <div className="space-y-6 px-5 py-5">
        {result.matches.length === 0 && (
          <p className="text-sm text-slate-700">
            No skills were recognised in the job description, so there is nothing to match.
          </p>
        )}

        {GROUPS.map((group) => {
          const items = result.matches.filter((match) => match.status === group.status);
          if (result.matches.length === 0) return null;
          return (
            <section key={group.status} aria-labelledby={`group-${group.status}`}>
              <div className="flex items-center gap-2">
                <h3 id={`group-${group.status}`} className="text-sm font-semibold text-slate-900">
                  {group.title}
                </h3>
                <Badge tone={group.tone}>{items.length}</Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{group.description}</p>

              {items.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">None.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {items.map((match) => (
                    <li key={match.name}>
                      <details className="rounded-lg border border-slate-200">
                        <summary className="flex cursor-pointer flex-wrap items-center gap-2 px-3 py-2 text-sm font-medium text-slate-900">
                          {match.name}
                          <Badge tone={IMPORTANCE_TONE[match.importance]}>
                            {IMPORTANCE_LABEL[match.importance]}
                          </Badge>
                        </summary>
                        <div className="space-y-3 border-t border-slate-100 px-3 py-3">
                          <p className="text-sm text-slate-700">{match.note}</p>
                          <div>
                            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                              Evidence in the resume
                            </h4>
                            <EvidenceList
                              items={match.evidence}
                              emptyText="No evidence found in the resume."
                            />
                          </div>
                          <div>
                            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                              Where the job description mentions it
                            </h4>
                            <EvidenceList
                              items={match.requirement_evidence}
                              emptyText="No matching line was recorded."
                            />
                          </div>
                        </div>
                      </details>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}

        <p className="text-xs text-slate-600">
          Evidence check: {result.validation.checked} pieces of evidence were compared with the
          original text; {result.validation.rejected} could not be verified and were not counted.
        </p>
      </div>
    </Card>
  );
}