import { AlertTriangle, Copy, X } from "lucide-react";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

import { useToast } from "./ui/Toast";
import { Button } from "./ui/Button";
import { Skeleton } from "./ui/States";

const Ctx = createContext({ open: () => {} });

/** useSource().open(citationId) opens the Source drawer from anywhere. */
export function useSource() {
  return useContext(Ctx);
}

export function SourceProvider({ children }) {
  const [id, setId] = useState(null);
  return (
    <Ctx.Provider value={{ open: setId }}>
      {children}
      {id && <SourceDrawer citationId={id} onClose={() => setId(null)} />}
    </Ctx.Provider>
  );
}

function Highlighted({ detail }) {
  const seg = detail.segment;
  if (!seg) return <p className="text-body text-ink">{detail.source_text}</p>;
  if (!seg.highlight) return <p className="text-body text-ink">{seg.text}</p>;
  const { start, end } = seg.highlight;
  return (
    <p className="text-body leading-7 text-ink">
      {seg.text.slice(0, start)}
      <mark className="rounded-sm bg-indigo-soft px-0.5 font-semibold text-ink">{seg.text.slice(start, end)}</mark>
      {seg.text.slice(end)}
    </p>
  );
}

function SourceDrawer({ citationId, onClose }) {
  const [detail, setDetail] = useState();
  const [error, setError] = useState();
  const toast = useToast();

  useEffect(() => {
    setDetail(undefined);
    api
      .citation(citationId)
      .then(setDetail)
      .catch((e) => setError(e.message));
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [citationId, onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/20" onClick={onClose}>
      <aside
        className="h-full w-full max-w-xl overflow-y-auto border-l border-line bg-white p-8 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
          <h2 className="text-section text-ink">Source</h2>
          <button
            onClick={onClose}
            className="rounded-control border border-line p-1.5 text-slate hover:text-ink"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {error && <p className="text-body text-bad">{error}</p>}
        {!detail && !error && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="mt-6 h-24 w-full rounded-card" />
          </div>
        )}
        {detail && (
          <>
            <h3 className="text-section text-ink">
              {detail.section
                ? /^\d/.test(detail.section)
                  ? `Section ${detail.section}`
                  : detail.section
                : "Document excerpt"}
            </h3>
            <p className="mt-1 text-table text-slate">
              {[detail.page ? `Page ${detail.page}` : null, detail.file_name, `Version ${detail.version_number}`]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {detail.validation_status === "not_found" && (
              <div className="mt-4 flex gap-2 rounded-card border border-warn/30 bg-warn-soft p-3 text-table text-warn">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                The quoted text could not be found in the document. Verify this item manually.
              </div>
            )}
            <div className="mt-5 space-y-5 rounded-card border border-line bg-canvas p-5">
              {detail.context_before && <p className="text-body leading-7 text-slate/70">{detail.context_before}</p>}
              <Highlighted detail={detail} />
              {detail.context_after && <p className="text-body leading-7 text-slate/70">{detail.context_after}</p>}
            </div>
            <p className="mt-3 text-table text-slate">Highlighted text is the excerpt this value was extracted from.</p>
            {detail.validation_status === "approximate" && (
              <p className="mt-1 text-table text-warn">
                Matched approximately: the document text differs slightly from the quote.
              </p>
            )}
            <div className="mt-4">
              <Button
                size="sm"
                onClick={() => {
                  navigator.clipboard?.writeText(detail.source_text);
                  toast("Excerpt copied");
                }}
              >
                <Copy className="h-3.5 w-3.5" /> Copy excerpt
              </Button>
            </div>
            <div className="mt-8">
              <p className="text-label uppercase text-slate">Quoted by the AI</p>
              <blockquote className="mt-2 border-l-2 border-amber-400 pl-3 text-body italic text-ink">
                “{detail.source_text}”
              </blockquote>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
