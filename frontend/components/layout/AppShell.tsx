"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Briefcase,
  FileText,
  LayoutDashboard,
  Menu,
  Settings,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  ready: boolean; // pages not built yet are shown as "Soon"
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, ready: true },
  { href: "/analyze", label: "Analyze Resume", icon: FileText, ready: true },
  { href: "/jobs", label: "Job Descriptions", icon: Briefcase, ready: false },
  { href: "/candidates", label: "Candidate Results", icon: Users, ready: false },
  { href: "/settings", label: "Settings", icon: Settings, ready: false },
];

function Brand() {
  return (
    <div className="flex items-center gap-2 px-5 py-5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
        H
      </span>
      <span className="text-lg font-semibold text-slate-900">HireIQ</span>
    </div>
  );
}

function NavList({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3 py-2">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

        if (!item.ready) {
          return (
            <span
              key={item.href}
              aria-disabled="true"
              className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-500"
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
              <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                Soon
              </span>
            </span>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
              active ? "bg-indigo-50 text-indigo-700" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarFooter() {
  return (
    <p className="border-t border-slate-100 px-5 py-4 text-xs text-slate-500">
      Demo data. The live backend connection arrives in Milestone 11.
    </p>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <Brand />
        <NavList pathname={pathname} />
        <SidebarFooter />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2 lg:hidden">
        <span className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            H
          </span>
          <span className="font-semibold text-slate-900">HireIQ</span>
        </span>
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          aria-expanded={menuOpen}
          className="rounded-lg p-2 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/40"
            aria-hidden="true"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-white shadow-xl">
            <div className="flex items-center justify-between pr-3">
              <Brand />
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
                className="rounded-lg p-2 text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <NavList pathname={pathname} onNavigate={() => setMenuOpen(false)} />
            <SidebarFooter />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <main id="main" className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}