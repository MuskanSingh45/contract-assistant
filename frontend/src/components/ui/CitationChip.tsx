import clsx from "clsx";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import type { Citation } from "@/lib/types";
import { citationLabel } from "@/lib/format";
import { useSource } from "@/components/SourceDrawer";

/** Inline citation chip: "Section 8.2 · Page 14 ↗". Opens the source drawer. */
export function CitationChip({
  citation,
  prefix,
  className,
}: {
  citation: Citation;
  prefix?: string;
  className?: string;
}) {
  const { open } = useSource();
  const missing = citation.validation_status === "not_found";
  return (
    <button
      type="button"
      onClick={() => open(citation.id)}
      title={missing ? "Quoted text could not be found in the document" : citation.source_text}
      className={clsx(
        "inline-flex items-center gap-1 rounded-control border px-2.5 py-1 text-table transition-colors",
        missing
          ? "border-warn/30 bg-warn-soft text-warn hover:border-warn"
          : "border-line bg-canvas text-indigo hover:border-indigo hover:bg-indigo-soft",
        className,
      )}
    >
      {missing && <AlertTriangle className="h-3.5 w-3.5" />}
      {prefix && <span className="text-slate">{prefix}</span>}
      {citationLabel(citation)}
      <ArrowUpRight className="h-3.5 w-3.5" />
    </button>
  );
}

/** First citation as a chip plus "+N" if there are more. */
export function Citations({ citations }: { citations: Citation[] }) {
  if (!citations.length) return <span className="text-meta text-slate">No source</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <CitationChip citation={citations[0]} />
      {citations.length > 1 && <span className="text-meta text-slate">+{citations.length - 1}</span>}
    </span>
  );
}
