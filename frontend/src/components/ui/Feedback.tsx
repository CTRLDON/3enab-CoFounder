import { LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "../../services/api";
import { Button } from "./Button";

export function ErrorNotice({ error, onRetry, children }: { error: unknown; onRetry?: () => void; children?: ReactNode }) {
  if (!error) return null;
  const message = error instanceof ApiError || error instanceof Error ? error.message : String(error);
  const code = error instanceof ApiError ? error.code : null;
  const hint =
    code === "agent_failure"
      ? "The model did not produce a usable answer, so nothing was invented in its place. Check the model status, then try again."
      : code === "approval_required"
        ? "This step waits for your explicit approval."
        : code === "version_conflict"
          ? "Someone changed the plan in the meantime. Reopen the node to work from the latest version."
          : null;
  return (
    <div role="alert" className="flex gap-3 rounded-lg border border-line bg-surface p-3.5 fade-in">
      <TriangleAlert className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{message}</p>
        {hint ? <p className="t-small text-muted mt-0.5">{hint}</p> : null}
        {children}
      </div>
      {onRetry ? <Button size="sm" onClick={onRetry}>Try again</Button> : null}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted t-small" role="status">
      <LoaderCircle className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="h-3.5 rounded bg-sunken animate-pulse" style={{ width: `${90 - i * 14}%` }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line p-6 text-center">
      <p className="font-medium">{title}</p>
      {children ? <div className="t-small text-muted mt-1">{children}</div> : null}
    </div>
  );
}
