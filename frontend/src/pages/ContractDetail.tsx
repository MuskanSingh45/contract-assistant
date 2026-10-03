import { Loader2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, errorMessage } from "@/lib/api";
import type { ContractDetail as Detail } from "@/lib/types";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
import { FilterSelect } from "@/components/ui/Select";
import { Async, Skeleton } from "@/components/ui/States";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/Toast";
import AnalysisTab from "@/components/contract/AnalysisTab";
import ObligationsTab from "@/components/contract/ObligationsTab";
import OverviewTab from "@/components/contract/OverviewTab";
import SummaryTab from "@/components/contract/SummaryTab";
import VersionsTab from "@/components/contract/VersionsTab";

type TabKey = "overview" | "analysis" | "obligations" | "versions" | "summary";

function contractBadge(c: Detail) {
  const s = c.version.analysis_status;
  if (s === "queued" || s === "processing") return <StatusBadge kind="neutral" label="Analyzing" />;
  if (s === "failed") return <StatusBadge kind="rejected" label="Analysis failed" />;
  if (s === "not_started") return <StatusBadge kind="neutral" label="Not analyzed" />;
  if (c.counts.open_clarifications) return <StatusBadge kind="conflict" />;
  if (c.counts.pending_reviews) return <StatusBadge kind="needs_review" />;
  return <StatusBadge kind="approved" />;
}

function AnalysisBanner({ contract, onAnalyze, busy }: { contract: Detail; onAnalyze: () => void; busy: boolean }) {
  const s = contract.version.analysis_status;
  if (s === "completed") return null;
  const running = s === "queued" || s === "processing";
  return (
    <Card className="mb-6 flex items-center justify-between gap-4 border-indigo-ring bg-indigo-soft p-5">
      <div className="flex items-center gap-3 text-body text-ink">
        {running && <Loader2 className="h-4 w-4 animate-spin text-indigo" />}
        {running
          ? "This version is being analyzed."
          : s === "failed"
            ? "The last analysis of this version failed."
            : "This version has not been analyzed yet."}
      </div>
      {running ? (
        <Link to={`/contracts/${contract.id}/analyzing`} className="text-body font-medium text-indigo hover:underline">
          View progress →
        </Link>
      ) : (
        <Button variant="primary" loading={busy} onClick={onAnalyze}>
          {s === "failed" ? "Retry analysis" : "Analyze now"}
        </Button>
      )}
    </Card>
  );
}

export default function ContractDetail() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const tab = (params.get("tab") as TabKey) || "overview";
  const versionParam = params.get("version") ?? undefined;
  const contract = useApi(() => api.getContract(id, versionParam), [id, versionParam]);
  const versions = useApi(() => api.versions(id), [id]);
  const [analyzing, setAnalyzing] = useState(false);

  const setParam = (k: string, v: string | null) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };

  async function reanalyze(versionId: string) {
    setAnalyzing(true);
    try {
      await api.analyze(id, versionId);
      navigate(`/contracts/${id}/analyzing`);
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <Async
      state={contract}
      skeleton={
        <div className="space-y-4">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-8 w-96" />
          <Skeleton className="mt-8 h-64 w-full rounded-card" />
        </div>
      }
    >
      {(c) => (
        <>
          <PageHeader
            breadcrumb={
              <>
                <Link to="/contracts" className="hover:text-ink">
                  Contracts
                </Link>{" "}
                / <span className="text-ink">{c.name}</span>
              </>
            }
            title={c.name}
            badge={contractBadge(c)}
            subtitle={
              <span className="flex flex-wrap items-center gap-x-3">
                {c.parties.length > 0 && <span>{c.parties.map((p) => p.name).join(" · ")}</span>}
                {c.parties.length > 0 && <span className="text-line">|</span>}
                <span>Version {c.version.version_number}</span>
                <span>·</span>
                <span>Uploaded {fmtDate(c.version.uploaded_at)}</span>
              </span>
            }
            actions={
              <>
                <Button onClick={() => navigate(`/contracts/upload?contract=${c.id}`)}>Upload New Version</Button>
                <Button
                  loading={analyzing}
                  onClick={() => reanalyze(c.version.id)}
                  disabled={c.version.analysis_status === "queued" || c.version.analysis_status === "processing"}
                >
                  Re-analyze
                </Button>
                <Button variant="primary" onClick={() => setParam("tab", "summary")}>
                  View Summary
                </Button>
              </>
            }
          />

          {versions.data && versions.data.length > 1 && (
            <div className="mb-6 flex items-center gap-3">
              <FilterSelect
                label="Version"
                value={c.version.id}
                options={versions.data.map((v) => ({
                  value: v.id,
                  label: `V${v.version_number}${v.is_latest ? " (current)" : ""} · ${fmtDate(v.uploaded_at)}`,
                }))}
                onChange={(v) => setParam("version", versions.data!.find((x) => x.id === v)?.is_latest ? null : v)}
              />
              {!c.version.is_latest && (
                <span className="text-body text-warn">Viewing an earlier version (not the current contract)</span>
              )}
            </div>
          )}

          <AnalysisBanner contract={c} busy={analyzing} onAnalyze={() => reanalyze(c.version.id)} />

          <Tabs<TabKey>
            value={tab}
            onChange={(k) => setParam("tab", k === "overview" ? null : k)}
            tabs={[
              { key: "overview", label: "Overview" },
              { key: "analysis", label: "Analysis", count: c.counts.open_clarifications },
              { key: "obligations", label: "Obligations" },
              { key: "versions", label: "Versions" },
              { key: "summary", label: "Summary" },
            ]}
          />

          {tab === "overview" && <OverviewTab contract={c} />}
          {tab === "analysis" && <AnalysisTab contract={c} onChanged={contract.reload} />}
          {tab === "obligations" && <ObligationsTab contractId={c.id} versionId={c.version.id} />}
          {tab === "versions" && <VersionsTab contractId={c.id} versionId={c.version.id} />}
          {tab === "summary" && <SummaryTab contractId={c.id} versionId={c.version.id} />}
        </>
      )}
    </Async>
  );
}
