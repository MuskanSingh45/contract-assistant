import clsx from "clsx";
import type { ExtractedItem, Obligation, Renewal } from "@/lib/types";
import { citationLabel, reviewStatusKind } from "@/lib/format";
import { StatusBadge } from "@/components/ui/Badge";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { CitationChip } from "@/components/ui/CitationChip";
import { ReviewActions } from "./ReviewActions";

/** The design's ExtractionItem card: label, value, confidence, review badge, source, actions. */
export function ExtractionItemCard({
  item,
  onReviewed,
  highlight,
}: {
  item: ExtractedItem;
  onReviewed: (res: { renewal: Renewal | null }) => void;
  highlight?: boolean;
}) {
  const cite = item.citations[0];
  const reviewed = item.review_status !== "pending";
  return (
    <div
      className={clsx(
        "rounded-card border bg-white p-6",
        highlight ? "border-indigo ring-1 ring-indigo" : "border-line",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="text-body text-slate">{item.label}</span>
        <div className="flex items-center gap-3">
          {item.origin === "human" ? (
            <span className="text-table text-indigo">Entered by reviewer</span>
          ) : (
            <ConfidenceBadge level={item.confidence} />
          )}
          <StatusBadge kind={reviewStatusKind(item.review_status, { conflict: item.in_open_clarification })} />
        </div>
      </div>
      <p className="mt-2 text-value text-ink">{item.display_value}</p>
      {item.review_status === "edited" && JSON.stringify(item.value) !== JSON.stringify(item.original_value) && (
        <p className="mt-1 text-table text-slate">Edited by reviewer · original extraction kept for audit</p>
      )}
      {item.ambiguity_note && <p className="mt-2 text-body text-slate">Flagged: {item.ambiguity_note}</p>}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <span className="flex items-center gap-2 text-table text-slate">
          Source
          {cite ? <CitationChip citation={cite} /> : <span>none</span>}
          {item.citations.length > 1 && <span>+{item.citations.length - 1} more</span>}
        </span>
        {!reviewed || item.review_status === "rejected" ? (
          <ReviewActions
            entityType="extracted_item"
            entityId={item.id}
            fieldName={item.field_name}
            value={item.value}
            label={item.label}
            onReviewed={onReviewed}
          />
        ) : (
          <span className="text-table text-slate">{cite ? citationLabel(cite) : ""}</span>
        )}
      </div>
    </div>
  );
}

/** Content fields of an obligation, in the shape ReviewActions edits. */
export function obligationValue(o: Obligation): Record<string, unknown> {
  return {
    description: o.description,
    responsible_party: o.responsible_party,
    frequency: o.frequency,
    due_date: o.due_date_source === "explicit" ? o.due_date : null,
  };
}
