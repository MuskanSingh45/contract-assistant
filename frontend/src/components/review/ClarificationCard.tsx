import { AlertCircle, GitCompareArrows, HelpCircle } from "lucide-react";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { Clarification, FieldName, Renewal } from "@/lib/types";
import { fmtDate, fmtDateTime } from "@/lib/format";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CitationChip } from "@/components/ui/CitationChip";
import { useToast } from "@/components/ui/Toast";
import { EditValueForm } from "./EditValueForm";
import { validateEditValue } from "./validation";

const kindBadge = {
  conflict: { kind: "conflict" as const, label: "Potential Conflict", Icon: GitCompareArrows },
  ambiguity: { kind: "clarification" as const, label: "Ambiguous wording", Icon: HelpCircle },
  missing: { kind: "clarification" as const, label: "Missing information", Icon: AlertCircle },
};

const why = {
  conflict:
    "The same field was found with different values in different places. The tool does not decide which one applies. Please confirm.",
  ambiguity: "The AI flagged the wording as unclear. Confirm the extracted value or enter the correct one.",
  missing:
    "Deadlines cannot be calculated without this information. Enter it, or dismiss if the contract has no fixed term.",
};

const emptyValue: Partial<Record<FieldName, Record<string, unknown>>> = {
  expiration_date: { date: "", date_text: "" },
  effective_date: { date: "", date_text: "" },
  notice_period: { value: 90, unit: "days", anchor: "expiration_date", purpose: "non_renewal" },
  renewal_terms: { type: "automatic", period_value: 12, period_unit: "months" },
  initial_term: { value: 1, unit: "years" },
};

/** Conflict / ambiguity / missing-information card with resolution (design: Conflicts & Ambiguities). */
export function ClarificationCard({
  clarification: c,
  onResolved,
  showContract,
}: {
  clarification: Clarification;
  onResolved: (renewal: Renewal | null) => void;
  showContract?: boolean;
}) {
  const toast = useToast();
  const [mode, setMode] = useState<"idle" | "custom">("idle");
  const [custom, setCustom] = useState<Record<string, unknown>>(
    (c.field_name && emptyValue[c.field_name]) || (c.options[0] ? {} : { date: "", date_text: "" }),
  );
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();
  const [showErrors, setShowErrors] = useState(false);
  const meta = kindBadge[c.kind];
  const open = c.status === "open";

  async function resolve(body: Parameters<typeof api.resolveClarification>[1], key: string) {
    setBusy(key);
    setError(undefined);
    try {
      const res = await api.resolveClarification(c.id, { ...body, note: note || undefined });
      toast(body.action === "dismiss" ? "Marked as reviewed" : "Answer saved · deadlines recalculated");
      onResolved(res.renewal);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <Card className={open ? "p-6" : "bg-canvas p-6"}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <StatusBadge
            kind={open ? meta.kind : c.status === "resolved" ? "approved" : "previous"}
            label={open ? meta.label : c.status === "resolved" ? "Resolved" : "Dismissed"}
          />
          {showContract && <span className="text-table text-slate">{c.contract_name}</span>}
        </div>
        <span className="text-table text-slate">
          {open ? "Review status: Open" : `Answered ${fmtDate(c.resolved_at)}`}
        </span>
      </div>
      <h3 className="mt-3 text-section text-ink">{c.question}</h3>

      {c.options.length > 0 && (
        <div className={`mt-4 grid gap-3 ${c.options.length > 1 ? "md:grid-cols-2" : ""}`}>
          {c.options.map((o, i) => {
            const chosen = o.review_status === "approved" || o.review_status === "edited";
            return (
              <div
                key={o.entity_id}
                className={`rounded-card border p-4 ${!open && chosen ? "border-ok bg-ok-soft" : "border-line bg-canvas"}`}
              >
                <p className="text-label uppercase text-slate">
                  Source {i + 1}
                  {!open && chosen ? " · selected" : ""}
                </p>
                <p className="mt-1 text-value text-ink">{o.display_value}</p>
                {o.citations[0] && (
                  <>
                    <p className="mt-1 text-table text-slate">“…{o.citations[0].source_text}…”</p>
                    <CitationChip citation={o.citations[0]} className="mt-2" />
                  </>
                )}
                {open && (
                  <Button
                    size="sm"
                    className="mt-3"
                    loading={busy === o.entity_id}
                    onClick={() => resolve({ action: "select", entity_id: o.entity_id }, o.entity_id)}
                  >
                    Use this value
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {open && (
        <>
          <p className="mt-4 text-body font-medium text-ink">Why it was flagged</p>
          <p className="mt-1 text-body text-slate">{why[c.kind]}</p>

          {mode === "custom" && c.field_name && (
            <div className="mt-4 rounded-card border border-indigo p-4">
              <p className="mb-3 text-label uppercase text-indigo">Your answer</p>
              <EditValueForm field={c.field_name} value={custom} onChange={setCustom} showErrors={showErrors} />
            </div>
          )}
          <label className="mt-4 block">
            <span className="mb-1 block text-table text-slate">Note (optional)</span>
            <textarea
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Confirmed with legal team on Oct 3."
              className="w-full rounded-control border border-line px-3 py-2 text-body focus:border-indigo focus:ring-2 focus:ring-indigo-ring"
            />
          </label>
          {error && <p className="mt-2 text-table text-bad">{error}</p>}

          <div className="mt-4 flex flex-wrap justify-end gap-2 border-t border-line pt-4">
            <Button loading={busy === "dismiss"} onClick={() => resolve({ action: "dismiss" }, "dismiss")}>
              Mark as reviewed
            </Button>
            {c.field_name && mode === "idle" && (
              <Button
                variant={c.options.length ? "secondary" : "primary"}
                onClick={() => {
                  setShowErrors(false);
                  setMode("custom");
                }}
              >
                {c.options.length ? "Enter a different value" : "Answer question"}
              </Button>
            )}
            {mode === "custom" && (
              <>
                <Button onClick={() => setMode("idle")}>Cancel</Button>
                <Button
                  variant="primary"
                  loading={busy === "custom"}
                  onClick={() => {
                    // Invalid answers never reach the API: reveal every message and wait for a fix.
                    if (c.field_name && Object.keys(validateEditValue(c.field_name, custom)).length) {
                      setShowErrors(true);
                      return;
                    }
                    resolve({ action: "custom", value: custom }, "custom");
                  }}
                >
                  Save answer
                </Button>
              </>
            )}
          </div>
        </>
      )}
      {!open && (c.resolution_note || c.resolved_at) && (
        <p className="mt-3 text-table text-slate">
          {c.resolution_note ? `Note: “${c.resolution_note}” · ` : ""}
          {fmtDateTime(c.resolved_at)}
        </p>
      )}
    </Card>
  );
}
