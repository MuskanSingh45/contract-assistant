import clsx from "clsx";
import type { Confidence } from "@/lib/types";
import { confidenceLabel } from "@/lib/format";

const color: Record<Confidence, string> = { high: "text-ok", medium: "text-warn", low: "text-slate" };

function Dot({ level }: { level: Confidence }) {
  return (
    <svg viewBox="0 0 12 12" className="h-3 w-3 shrink-0" aria-hidden>
      <circle
        cx="6"
        cy="6"
        r="5"
        fill={level === "high" ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.5"
      />
      {level === "medium" && <path d="M6 1a5 5 0 0 0 0 10z" fill="currentColor" />}
    </svg>
  );
}

/** ConfidenceBadge (secondary metadata). `short` renders "High" instead of "High confidence". */
export function ConfidenceBadge({
  level,
  short,
  className,
}: {
  level: Confidence;
  short?: boolean;
  className?: string;
}) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-table", color[level], className)}>
      <Dot level={level} />
      {short ? level[0].toUpperCase() + level.slice(1) : confidenceLabel[level]}
    </span>
  );
}
