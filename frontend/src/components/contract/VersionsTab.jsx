import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import { fmtDate } from "@/lib/format";
import { Card, SectionTitle } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Async, EmptyState, TableSkeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
export default function VersionsTab({ contractId, versionId }) {
  const a = useApi(() => api.versions(contractId), [contractId]);
  const [selected, setSelected] = useState(versionId);
  const [changes, setChanges] = useState();
  const [err, setErr] = useState("");
  const toast = useToast();
  useEffect(() => {
    const v = a.data?.find((x) => x.id === selected);
    if (v?.analysis_status === "completed" && v.version_number > 1)
      api
        .versionChanges(contractId, selected)
        .then(setChanges)
        .catch((e) => setErr(errorMessage(e)));
    else setChanges(undefined);
  }, [a.data, contractId, selected]);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section>
        <SectionTitle
          action={
            <Link to={`/contracts/upload?contract=${contractId}`}>
              <Button>Upload New Version</Button>
            </Link>
          }
        >
          Versions
        </SectionTitle>
        <Async state={a} skeleton={<TableSkeleton />}>
          {(items) => (
            <div className="space-y-3">
              {items.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelected(v.id)}
                  className={`w-full text-left ${selected === v.id ? "rounded-card ring-1 ring-indigo" : ""}`}
                >
                  <Card className="p-5">
                    <div className="flex justify-between">
                      <b>Version {v.version_number}</b>
                      <StatusBadge kind={v.is_latest ? "current" : "previous"} />
                    </div>
                    <p className="mt-2 text-body text-slate">Uploaded {fmtDate(v.uploaded_at)}</p>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-table">
                      <span>File name</span>
                      <span className="text-right">{v.file_name}</span>
                      <span>Analysis status</span>
                      <span className="text-right">{v.analysis_status}</span>
                      <span>Changes</span>
                      <span className="text-right">{v.change_count ?? "—"}</span>
                    </div>
                  </Card>
                </button>
              ))}
            </div>
          )}
        </Async>
      </section>
      <section>
        <SectionTitle>
          What changed in Version {a.data?.find((v) => v.id === selected)?.version_number ?? "—"}
        </SectionTitle>
        {err && <p className="text-bad">{err}</p>}
        {!changes || !changes.items.length ? (
          <EmptyState title="No changes from the previous version" text="This version has no changes to review." />
        ) : (
          <div className="space-y-4">
            {changes.items.map((ch) => (
              <Card key={ch.id} className="p-5">
                {ch.change_type === "modified" &&
                  (ch.previous_review_status === "approved" || ch.previous_review_status === "edited") && (
                    <div className="mb-4 rounded-control bg-warn-soft p-3 text-warn">
                      <b>Potentially stale</b>
                      <p>
                        This information was approved from the previous version, but the new version may contain
                        different information.
                      </p>
                    </div>
                  )}
                <div className="flex justify-between">
                  <b className="capitalize">{ch.field_name.replace(/_/g, " ")}</b>
                  {ch.change_type === "modified" &&
                    (ch.previous_review_status === "approved" || ch.previous_review_status === "edited") && (
                      <StatusBadge kind="stale" />
                    )}
                </div>
                {ch.change_type === "modified" ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-card border border-line p-4">
                      <small className="text-label text-slate">
                        {ch.previous_review_status === "approved" || ch.previous_review_status === "edited"
                          ? "PREVIOUSLY APPROVED"
                          : "PREVIOUS"}{" "}
                        · V{(a.data?.find((v) => v.id === selected)?.version_number ?? 2) - 1}
                      </small>
                      <p>{ch.previous_display ?? "—"}</p>
                    </div>
                    <div className="rounded-card border border-indigo p-4">
                      <small className="text-label text-indigo">NEW EXTRACTED VALUE</small>
                      <p>{ch.new_display ?? "—"}</p>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3">
                    <b>{ch.change_type === "added" ? "Added" : "Removed"}:</b>{" "}
                    {ch.change_type === "added" ? ch.new_display : ch.previous_display}
                  </p>
                )}
                {ch.change_type === "modified" && ch.new_entity_id && (
                  <div className="mt-4 flex justify-end gap-2">
                    <Link to={`/review/${ch.entity_type}/${ch.new_entity_id}`}>
                      <Button size="sm">Review V{a.data?.find((v) => v.id === selected)?.version_number} value</Button>
                    </Link>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={async () => {
                        try {
                          await api.review({
                            entity_type: ch.entity_type,
                            entity_id: ch.new_entity_id,
                            action: "approve",
                          });
                          toast("New version value approved");
                          setChanges(await api.versionChanges(contractId, selected));
                        } catch (e) {
                          toast(errorMessage(e), "error");
                        }
                      }}
                    >
                      Approve V{a.data?.find((v) => v.id === selected)?.version_number} value
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
