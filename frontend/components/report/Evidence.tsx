import type { Evidence } from "@/lib/types";

export function EvidenceList({ items, emptyText }: { items: Evidence[]; emptyText?: string }) {
  if (items.length === 0) {
    return emptyText ? <p className="text-sm text-slate-600">{emptyText}</p> : null;
  }
  return (
    <ul className="space-y-1">
      {items.map((item, index) => (
        <li
          key={`${item.snippet}-${index}`}
          className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-800"
        >
          <span className="mr-2 text-xs font-medium uppercase tracking-wide text-slate-600">
            {item.section ?? item.source}
          </span>
          &ldquo;{item.snippet}&rdquo;
        </li>
      ))}
    </ul>
  );
}