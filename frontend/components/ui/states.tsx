import type { ReactNode } from "react";
import { AlertIcon, InboxIcon } from "./icons";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <span className="rounded-full bg-slate-100 p-3 text-slate-500">
        <InboxIcon className="h-6 w-6" />
      </span>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-600">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-6">
      <div className="flex items-start gap-3">
        <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
        <div>
          <h2 className="text-base font-semibold text-red-900">{title}</h2>
          <p className="mt-1 text-sm text-red-800">{message}</p>
          {action && <div className="mt-4">{action}</div>}
        </div>
      </div>
    </div>
  );
}