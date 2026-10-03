import { Check, FileText, Filter } from "lucide-react";

import { Button } from "./Button";
import { Card } from "./Card";

export function EmptyState({ icon = "file", title, text, action }) {
  const Icon = { file: FileText, check: Check, filter: Filter }[icon];
  return (
    <Card className="flex flex-col items-center px-6 py-12 text-center">
      <div className={`mb-4 rounded-card p-3 ${icon === "check" ? "bg-ok-soft text-ok" : "bg-canvas text-slate"}`}>
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-section text-ink">{title}</h3>
      <p className="mt-2 max-w-sm text-body text-slate">{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </Card>
  );
}

const TITLES = {
  NETWORK_ERROR: "Cannot reach the server",
  TIMEOUT: "The server is not responding",
  INTERNAL_ERROR: "Something went wrong on the server",
};

export function ErrorState({ error, onRetry }) {
  return (
    <Card role="alert" className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-canvas text-lg font-semibold text-ink">
        !
      </div>
      <h3 className="text-section text-ink">{TITLES[error.code] ?? "Something went wrong"}</h3>
      <p className="mt-2 max-w-sm text-body text-slate">{error.message}</p>
      {error.requestId && <p className="mt-2 font-mono text-meta text-slate">Reference: {error.requestId}</p>}
      {onRetry && (
        <Button className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Card>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-full bg-line/70 ${className}`} />;
}

/** Table-shaped loading skeleton, same rhythm on every list page. */
export function TableSkeleton({ rows = 4 }) {
  return (
    <Card className="p-6">
      <div className="mb-6 flex gap-12">
        {["w-40", "w-28", "w-20", "w-16"].map((w) => (
          <Skeleton key={w} className={`h-3 ${w}`} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-12 border-t border-line py-4">
          <Skeleton className="h-3 w-1/4" />
          <Skeleton className="h-3 w-1/5" />
          <Skeleton className="h-3 w-1/6" />
          <Skeleton className="h-5 w-20" />
        </div>
      ))}
    </Card>
  );
}

/** Loading/error wrapper: renders children only once data is available. */
export function Async({ state, children, skeleton }) {
  if (state.error && !state.data) return <ErrorState error={state.error} onRetry={state.reload} />;
  if (state.data === undefined) return <>{skeleton ?? <TableSkeleton />}</>;
  return <>{children(state.data)}</>;
}
