import { Skeleton } from "@/components/ui/primitives";

export default function Loading() {
  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <span className="sr-only">Loading report…</span>
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-9 w-72" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}