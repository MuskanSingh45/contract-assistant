import { ChevronLeft, ChevronRight, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "@/lib/api";

import { citationLabel, fmtDateTime, reviewStatusKind } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { CitationChip } from "@/components/ui/CitationChip";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { ConfirmDialog } from "@/components/ui/Dialog";
import { Async, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { EditValueForm, obligationEditValue } from "@/components/review/EditValueForm";
import { obligationValue } from "@/components/review/ExtractionItemCard";

function SourcePanel({ citationId }) {
  const [d, setD] = useState();
  useEffect(() => {
    setD(undefined);
    api
      .citation(citationId)
      .then(setD)
      .catch(() => {});
  }, [citationId]);
  if (!d) return <Skeleton className="h-48 w-full rounded-card" />;
  const seg = d.segment;
  return (
    <Card className="bg-canvas p-6">
      <div className="flex items-start justify-between border-b border-line pb-3">
        <h3 className="text-section text-ink">
          {d.section ? (/^\d/.test(d.section) ? `Section ${d.section}` : d.section) : "Document excerpt"}
        </h3>
        {d.page && <span className="text-table text-slate">Page {d.page}</span>}
      </div>
      {d.context_before && <p className="mt-4 text-body leading-7 text-slate/70">{d.context_before}</p>}
      <div className="mt-4 border-l-4 border-amber-400 pl-4 text-body leading-7 text-ink">
        {seg?.highlight ? (
          <>
            {seg.text.slice(0, seg.highlight.start)}
            <mark className="rounded-sm bg-indigo-soft px-0.5 font-semibold">
              {seg.text.slice(seg.highlight.start, seg.highlight.end)}
            </mark>
            {seg.text.slice(seg.highlight.end)}
          </>
        ) : (
          (seg?.text ?? d.source_text)
        )}
      </div>
      {d.context_after && <p className="mt-4 text-body leading-7 text-slate/70">{d.context_after}</p>}
      {d.validation_status === "not_found" && (
        <p className="mt-4 rounded-control bg-warn-soft p-3 text-table text-warn">
          The AI's quote “{d.source_text}” could not be found in the document. Verify this item manually.
        </p>
      )}
      <p className="mt-4 text-table text-slate">
        {d.file_name} · Version {d.version_number}
      </p>
    </Card>
  );
}

function ReviewBody({ detail, onDone }) {
  const toast = useToast();
  const isObligation = detail.entity_type === "obligation";
  const item = detail.item;
  const ext = item;
  const obl = item;
  const label = isObligation ? "Obligation" : ext.label;
  const currentValue = isObligation ? obligationValue(obl) : ext.value;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(currentValue);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState();
  const [error, setError] = useState();
  const [rejecting, setRejecting] = useState(false);
  const [citationIdx, setCitationIdx] = useState(0);
  const history = useApi(() => api.reviewHistory(detail.entity_type, item.id), [item.id, item.review_status]);

  const originalDisplay = isObligation
    ? String(obl.original_value.description ?? obl.description)
    : ext.original_display_value;
  const currentDisplay = isObligation ? obl.description : ext.display_value;
  const changedByHuman = item.review_status === "edited" && originalDisplay !== currentDisplay;

  async function act(action) {
    setBusy(action);
    setError(undefined);
    try {
      const value = action !== "edit" ? undefined : isObligation ? obligationEditValue(currentValue, draft) : draft;
      await api.review({ entity_type: detail.entity_type, entity_id: item.id, action, value, note: note || undefined });
      toast(`${label} ${action === "approve" ? "approved" : action === "edit" ? "saved & approved" : "rejected"}`);
      setRejecting(false);
      onDone();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(undefined);
    }
  }

  const cite = item.citations[citationIdx];
  return (
    <>
      <div className="grid gap-8 pb-28 lg:grid-cols-2">
        <div className="space-y-6">
          <h2 className="text-section text-ink">Extracted Information</h2>
          <Card className="p-6">
            <div className="flex justify-between">
              <span className="text-label uppercase text-slate">Original extraction</span>
              <span className="text-table text-slate">Read-only</span>
            </div>
            <p className="mt-3 text-value text-ink">{originalDisplay}</p>
            <div className="mt-4 grid grid-cols-2 gap-3 text-body">
              <span className="text-slate">
                Field <span className="text-ink">{label}</span>
              </span>
              {ext.origin === "human" ? (
                <span className="text-indigo">Entered by reviewer</span>
              ) : (
                <ConfidenceBadge level={item.confidence} />
              )}
              <span className="text-slate">
                Status{" "}
                <span className="text-ink">
                  {
                    { pending: "Needs Review", approved: "Approved", edited: "Edited", rejected: "Rejected" }[
                      item.review_status
                    ]
                  }
                </span>
              </span>
              <span>{item.citations[0] && <CitationChip citation={item.citations[0]} />}</span>
            </div>
            {item.ambiguity_note && <p className="mt-4 text-body text-warn">Flagged: {item.ambiguity_note}</p>}
            {isObligation && obl.frequency_text && (
              <p className="mt-4 text-body text-slate">Timing as written: “{obl.frequency_text}”</p>
            )}
          </Card>

          {changedByHuman && !editing && (
            <Card className="border-indigo p-6">
              <div className="flex justify-between">
                <span className="text-label uppercase text-indigo">User-edited value</span>
                <span className="text-table text-slate">Edited by reviewer</span>
              </div>
              <p className="mt-3 text-value text-ink">{currentDisplay}</p>
            </Card>
          )}

          {editing && (
            <Card className="border-2 border-indigo p-6">
              <div className="mb-4 flex justify-between">
                <span className="text-label uppercase text-indigo">User-edited value</span>
                <span className="text-table text-slate">Editing</span>
              </div>
              <EditValueForm field={isObligation ? "obligation" : ext.field_name} value={draft} onChange={setDraft} />
              <label className="mt-4 block">
                <span className="mb-1 block text-body text-ink">Note (optional)</span>
                <textarea
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="w-full rounded-control border border-line px-3 py-2 text-body focus:border-indigo focus:ring-2 focus:ring-indigo-ring"
                />
              </label>
              <p className="mt-3 text-table text-slate">The original extraction is kept for reference and audit.</p>
            </Card>
          )}
          {error && <p className="text-body text-bad">{error}</p>}

          <div className="space-y-1">
            {(history.data ?? []).map((h) => (
              <p key={h.id} className="flex items-center gap-2 text-table text-slate">
                <Clock className="h-3.5 w-3.5" />
                {{ approve: "Approved", edit: "Edited", reject: "Rejected" }[h.action]}
                {h.clarification_id ? " via clarification" : ""} · {fmtDateTime(h.reviewed_at)}
                {h.note ? ` · “${h.note}”` : ""}
              </p>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-section text-ink">Source</h2>
            {item.citations.length > 1 && (
              <div className="flex gap-1">
                {item.citations.map((c, i) => (
                  <button
                    key={c.id}
                    onClick={() => setCitationIdx(i)}
                    className={`rounded-control px-2 py-1 text-table ${i === citationIdx ? "bg-indigo-soft text-indigo" : "text-slate hover:text-ink"}`}
                  >
                    {citationLabel(c)}
                  </button>
                ))}
              </div>
            )}
          </div>
          {cite ? (
            <SourcePanel citationId={cite.id} />
          ) : (
            <Card className="p-6 text-body text-slate">No source citation (value entered by a reviewer).</Card>
          )}
        </div>
      </div>

      <div className="fixed bottom-0 left-60 right-0 border-t border-line bg-white/95 px-10 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <p className="text-body text-slate">
            {editing
              ? "Saving stores your value as the approved record."
              : "Approving adds this value to the approved contract record."}
          </p>
          <div className="flex gap-2">
            {editing ? (
              <Button
                onClick={() => {
                  setEditing(false);
                  setDraft(currentValue);
                }}
              >
                Cancel edit
              </Button>
            ) : (
              <Button
                onClick={() => {
                  setDraft(currentValue);
                  setEditing(true);
                }}
              >
                Edit
              </Button>
            )}
            <Button variant="danger" onClick={() => setRejecting(true)}>
              Reject
            </Button>
            {editing ? (
              <Button variant="primary" loading={busy === "edit"} onClick={() => act("edit")}>
                Save & Approve
              </Button>
            ) : (
              <Button variant="primary" loading={busy === "approve"} onClick={() => act("approve")}>
                Approve
              </Button>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={rejecting}
        title="Reject extracted information?"
        danger
        confirmLabel="Reject"
        busy={busy === "reject"}
        text="This will mark the extracted information as rejected. It stays in the record but is excluded from deadlines."
        onConfirm={() => act("reject")}
        onCancel={() => setRejecting(false)}
      />
    </>
  );
}

export default function ReviewItem() {
  const { entityType = "", entityId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queue = location.state?.queue ?? [];
  const pos = queue.findIndex(([, id]) => id === entityId);
  const detail = useApi(() => api.item(entityType, entityId), [entityType, entityId]);

  const go = (ref) => (ref ? navigate(`/review/${ref[0]}/${ref[1]}`, { state: { queue } }) : navigate("/review"));
  const next = () => go(pos >= 0 ? queue[pos + 1] : undefined);

  return (
    <Async state={detail}>
      {(d) => (
        <>
          <PageHeader
            breadcrumb={
              <div className="flex items-center justify-between">
                <span>
                  <Link to="/review" className="hover:text-ink">
                    Review Queue
                  </Link>{" "}
                  / <span className="text-ink">{d.entity_type === "obligation" ? "Obligation" : d.item.label}</span>
                </span>
                {pos >= 0 && (
                  <span className="flex items-center gap-2">
                    Item {pos + 1} of {queue.length}
                    <button disabled={pos === 0} onClick={() => go(queue[pos - 1])} className="disabled:opacity-30">
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      disabled={pos === queue.length - 1}
                      onClick={() => go(queue[pos + 1])}
                      className="disabled:opacity-30"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </span>
                )}
              </div>
            }
            title={d.entity_type === "obligation" ? d.item.description : d.item.label}
            badge={
              <>
                <StatusBadge
                  kind={reviewStatusKind(d.item.review_status, { conflict: d.item.in_open_clarification })}
                />
                <Link to={`/contracts/${d.contract_id}`} className="text-body text-slate hover:text-indigo">
                  {d.contract_name} · Version {d.version_number}
                  {d.is_latest_version ? "" : " (earlier version)"}
                </Link>
              </>
            }
          />
          {d.item.in_open_clarification && (
            <Card className="mb-6 border-bad/20 bg-bad-soft p-4 text-body text-bad">
              This value conflicts with another statement in the contract. Resolve it on the{" "}
              <Link to="/review" className="font-medium underline">
                Review Queue
              </Link>{" "}
              clarification card so both sources are compared side by side.
            </Card>
          )}
          <ReviewBody key={d.item.id} detail={d} onDone={next} />
        </>
      )}
    </Async>
  );
}
