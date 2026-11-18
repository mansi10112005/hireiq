import Link from "next/link";
import { Card, CardHeader } from "@/components/ui/primitives";

const LINKS = [
  { href: "/", label: "Normal" },
  { href: "/?demo=empty", label: "Empty state" },
  { href: "/?demo=slow", label: "Slow loading" },
  { href: "/?demo=error", label: "Error state" },
];

export function DemoStates() {
  if (process.env.NODE_ENV === "production") return null;

  return (
    <Card>
      <CardHeader
        title="Developer tools: screen states"
        description="Only visible in development. Use these links to see how the dashboard looks in each state."
      />
      <div className="flex flex-wrap gap-2 px-5 py-4">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
          >
            {link.label}
          </Link>
        ))}
      </div>
    </Card>
  );
}