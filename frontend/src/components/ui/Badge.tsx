import clsx from "clsx";
import type { StatusKind } from "@/lib/format";

const variants: Record<StatusKind, [string, string]> = {
  approved: ["Approved", "bg-ok-soft text-ok"],
  confirmed: ["Confirmed", "bg-ok-soft text-ok"],
  completed: ["Completed", "bg-ok-soft text-ok"],
  needs_review: ["Needs Review", "bg-warn-soft text-warn"],
  stale: ["Potentially Stale", "bg-warn-soft text-warn"],
  clarification: ["Clarification Needed", "bg-warn-soft text-warn"],
  conflict: ["Potential Conflict", "bg-bad-soft text-bad"],
  overdue: ["Overdue", "bg-bad-soft text-bad"],
  rejected: ["Rejected", "bg-bad-soft text-bad"],
  edited: ["Edited", "bg-indigo-soft text-indigo"],
  upcoming: ["Upcoming", "bg-indigo-soft text-indigo"],
  current: ["Current", "bg-indigo-soft text-indigo"],
  previous: ["Previous", "bg-canvas text-slate"],
  neutral: ["", "bg-canvas text-slate"],
};

/** StatusBadge from the design system. `label` overrides the default text. */
export function StatusBadge({ kind, label, className }: { kind: StatusKind; label?: string; className?: string }) {
  const [text, color] = variants[kind];
  return (
    <span
      className={clsx(
        "inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-table font-medium",
        color,
        className,
      )}
    >
      {label ?? text}
    </span>
  );
}

export function CountPill({ n, tone = "neutral" }: { n: number; tone?: "neutral" | "warn" }) {
  return (
    <span
      className={clsx(
        "inline-flex min-w-[20px] items-center justify-center rounded-full px-1.5 text-meta font-semibold",
        tone === "warn" ? "bg-warn-soft text-warn" : "bg-canvas text-slate",
      )}
    >
      {n}
    </span>
  );
}
