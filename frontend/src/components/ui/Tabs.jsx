import clsx from "clsx";
import { CountPill } from "./Badge";

/** Underline tabs (contract details). */
export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-6 flex gap-8 border-b border-line">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={clsx(
            "-mb-px flex items-center gap-2 border-b-2 pb-3 text-body",
            value === t.key ? "border-indigo font-medium text-ink" : "border-transparent text-slate hover:text-ink",
          )}
        >
          {t.label}
          {!!t.count && <CountPill n={t.count} tone="warn" />}
        </button>
      ))}
    </div>
  );
}

/** Segmented pill tabs (Obligations filter, Analysis sub-tabs). */
export function PillTabs({ tabs, value, onChange }) {
  return (
    <div className="mb-5 inline-flex flex-wrap gap-1 rounded-card bg-canvas p-1">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={clsx(
            "rounded-control px-4 py-1.5 text-body",
            value === t.key ? "bg-white font-medium text-ink shadow-sm" : "text-slate hover:text-ink",
          )}
        >
          {t.label}
          {t.count !== undefined && <span className="ml-1.5 text-slate">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}
