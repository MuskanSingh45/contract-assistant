import { citationLabel, fmtDaysUntil, fmtLongDate } from "@/lib/format";
import { obligationKind } from "./ObligationTable";
import { Card, Field } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { CitationChip } from "@/components/ui/CitationChip";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { ReviewActions } from "@/components/review/ReviewActions";
import { obligationValue } from "@/components/review/ExtractionItemCard";
export default function ObligationDetail({ item, onReviewed, onStatus }) {
  const c = item.citations[0];
  return (
    <Card className="p-5">
      <p className="text-meta text-slate">Obligation · {item.contract_name}</p>
      <div className="mt-3 flex justify-between gap-2">
        <h2 className="text-section">{item.description}</h2>
        <StatusBadge kind={obligationKind(item)} />
      </div>
      <div className="mt-4 overflow-hidden rounded-card border border-line">
        <Field label="Responsible party">{item.responsible_party ?? "—"}</Field>
        <Field label="Frequency">{item.frequency_text ?? item.frequency ?? "—"}</Field>
        <Field label="Next deadline">
          {fmtLongDate(item.due_date)} {fmtDaysUntil(item.days_until_due)}{" "}
          {item.due_date_source === "calculated" && "(calculated)"}
        </Field>
      </div>
      <h3 className="mt-5 text-section">Source</h3>
      {c && (
        <div className="mt-2 rounded-card bg-canvas p-4">
          <p className="text-table text-slate">{citationLabel(c)}</p>
          <blockquote className="mt-2 border-l-4 border-amber-400 pl-3 text-body">“{c.source_text}”</blockquote>
          <CitationChip className="mt-3" citation={c} />
        </div>
      )}
      {item.ambiguity_note && <p className="mt-3 text-body text-warn">Flagged: {item.ambiguity_note}</p>}
      <h3 className="mt-5 text-section">Review</h3>
      <p className="mt-2 text-body text-slate">
        <ConfidenceBadge level={item.confidence} /> · Review status: {item.review_status}
      </p>
      <div className="mt-3" />
      <ReviewActions
        entityType="obligation"
        entityId={item.id}
        value={obligationValue(item)}
        label={item.description}
        citation={c}
        onReviewed={onReviewed}
      />
      <label className="mt-5 block text-table text-slate">
        Operational status
        <select
          value={item.status}
          onChange={(e) => onStatus(e.target.value)}
          className="ml-3 rounded-control border border-line bg-white p-2 text-body text-ink"
        >
          <option value="open">Open</option>
          <option value="completed">Completed</option>
          <option value="not_applicable">Not applicable</option>
        </select>
      </label>
    </Card>
  );
}
