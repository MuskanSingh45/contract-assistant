import { useState } from "react";
import { api, errorMessage } from "@/lib/api";

import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useSource } from "@/components/SourceDrawer";
import { EditValueForm, obligationEditValue } from "./EditValueForm";
import { validateEditValue } from "./validation";

/** View source · Edit · Reject · Approve, exactly as in the design's ExtractionItem. */
export function ReviewActions({ entityType, entityId, fieldName, value, label, citation, onReviewed, size = "sm" }) {
  const toast = useToast();
  const { open } = useSource();
  const [busy, setBusy] = useState();
  const [rejecting, setRejecting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [note, setNote] = useState("");
  const [error, setError] = useState();
  const [showErrors, setShowErrors] = useState(false);
  const editField = entityType === "obligation" ? "obligation" : fieldName;

  async function act(action) {
    // Invalid edits never reach the API: reveal every message and wait for a fix.
    if (action === "edit" && Object.keys(validateEditValue(editField, draft)).length) {
      setShowErrors(true);
      return;
    }
    setBusy(action);
    setError(undefined);
    try {
      const payload =
        action !== "edit" ? undefined : entityType === "obligation" ? obligationEditValue(value, draft) : draft;
      const res = await api.review({
        entity_type: entityType,
        entity_id: entityId,
        action,
        value: payload,
        note: note || undefined,
      });
      toast(`${label} ${action === "approve" ? "approved" : action === "reject" ? "rejected" : "updated"}`);
      setRejecting(false);
      setEditing(false);
      setNote("");
      onReviewed(res);
    } catch (e) {
      const msg = errorMessage(e);
      if (action === "edit") setError(msg);
      else toast(msg, "error");
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {citation && (
        <Button size={size} onClick={() => open(citation.id)}>
          View source
        </Button>
      )}
      <Button
        size={size}
        onClick={() => {
          setDraft(value);
          setError(undefined);
          setShowErrors(false);
          setEditing(true);
        }}
      >
        Edit
      </Button>
      <Button size={size} variant="danger" onClick={() => setRejecting(true)}>
        Reject
      </Button>
      <Button size={size} variant="primary" loading={busy === "approve"} onClick={() => act("approve")}>
        Approve
      </Button>

      <ConfirmDialog
        open={rejecting}
        title="Reject extracted information?"
        text="This will mark the extracted information as rejected. It stays in the record but is excluded from deadlines."
        confirmLabel="Reject"
        danger
        busy={busy === "reject"}
        onConfirm={() => act("reject")}
        onCancel={() => setRejecting(false)}
      />
      <ConfirmDialog
        open={editing}
        title={`Edit ${label.toLowerCase()}`}
        text="The original extraction is kept for reference and audit."
        confirmLabel="Save & Approve"
        busy={busy === "edit"}
        onConfirm={() => act("edit")}
        onCancel={() => setEditing(false)}
      >
        <EditValueForm field={editField} value={draft} onChange={setDraft} showErrors={showErrors} />
        <label className="mt-3 block">
          <span className="mb-1 block text-table text-slate">Note (optional)</span>
          <textarea
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full rounded-control border border-line px-3 py-2 text-body focus:border-indigo focus:ring-2 focus:ring-indigo-ring"
          />
        </label>
        {error && <p className="mt-2 text-table text-bad">{error}</p>}
      </ConfirmDialog>
    </div>
  );
}
