import { Skeleton } from "@/components/ui/primitives";

export default function Loading() {
  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <span className="sr-only">Loading results…</span>
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
}