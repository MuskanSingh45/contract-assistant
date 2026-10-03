import { useEffect, useId } from "react";
import { Button } from "./Button";

export function ConfirmDialog({ open, title, text, confirmLabel, danger, busy, onConfirm, onCancel, children }) {
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && !busy && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/30 p-4" onClick={onCancel}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md rounded-card bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id={titleId} className="text-section text-ink">
          {title}
        </h3>
        {text && <p className="mt-2 text-body text-slate">{text}</p>}
        {children && <div className="mt-4">{children}</div>}
        <div className="mt-6 flex justify-end gap-2">
          <Button onClick={onCancel}>Cancel</Button>
          <Button
            variant="primary"
            className={danger ? "!bg-bad hover:!bg-bad/90" : undefined}
            loading={busy}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
