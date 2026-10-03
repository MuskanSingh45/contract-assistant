import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisState, ContractDetail } from "@/lib/types";
import { PageHeader, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ErrorState, TableSkeleton } from "@/components/ui/States";
const steps = [
  "Uploading document",
  "Reading document",
  "Extracting contract information",
  "Validating citations",
  "Checking conflicts & calculating deadlines",
  "Preparing results",
];
export default function Analyzing() {
  const { id = "" } = useParams();
  const [state, setState] = useState<AnalysisState>(),
    [contract, setContract] = useState<ContractDetail>(),
    [error, setError] = useState<ApiError>();
  const [reload, setReload] = useState(0);
  const retry = useCallback(() => setReload((x) => x + 1), []);
  useEffect(() => {
    let live = true;
    api
      .getContract(id)
      .then((x) => live && setContract(x))
      .catch((e) => live && setError(e instanceof ApiError ? e : new ApiError("ERROR", String(e), 0)));
    return () => {
      live = false;
    };
  }, [id]);
  useEffect(() => {
    let timer: number | undefined,
      live = true;
    const poll = async () => {
      try {
        const s = await api.analysis(id);
        if (!live) return;
        setState(s);
        if (s.analysis_status === "queued" || s.analysis_status === "processing") timer = window.setTimeout(poll, 2000);
      } catch (e) {
        if (live) setError(e instanceof ApiError ? e : new ApiError("ERROR", String(e), 0));
      }
    };
    poll();
    return () => {
      live = false;
      if (timer) clearTimeout(timer);
    };
  }, [id, reload]);
  const stage = state?.analysis_stage;
  const current =
    stage === "parsing"
      ? 1
      : stage === "extracting"
        ? 2
        : stage === "validating"
          ? 3
          : stage === "analyzing"
            ? 4
            : stage === "complete"
              ? 5
              : state?.analysis_status === "queued"
                ? 1
                : 0;
  const failed = state?.analysis_status === "failed",
    done = state?.analysis_status === "completed";
  async function retryAnalysis() {
    try {
      await api.analyze(id);
      setState(undefined);
      retry();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError("ERROR", String(e), 0));
    }
  }
  if (error && !contract) return <ErrorState error={error} onRetry={() => location.reload()} />;
  if (!contract) return <TableSkeleton />;
  return (
    <>
      <PageHeader
        breadcrumb="Contracts / Upload Contract"
        title="Analyzing contract"
        subtitle="This usually takes one to three minutes on a laptop. You can leave this page and come back."
      />
      <div className="mx-auto max-w-4xl">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex gap-4">
              <span className="rounded-control bg-indigo-soft p-3 text-table font-semibold text-indigo">
                {contract.version.file_name.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF"}
              </span>
              <span>
                <b>{contract.version.file_name}</b>
                <small className="block text-slate">
                  {
                    {
                      not_started: "Not started",
                      queued: "Queued",
                      processing: "Analyzing…",
                      completed: "Analysis complete",
                      failed: "Analysis failed",
                    }[state?.analysis_status ?? contract.version.analysis_status]
                  }
                </small>
              </span>
            </div>
            <b>Step {done ? 6 : failed ? current + 1 : current + 1} of 6</b>
          </div>
          <div className="mt-6 h-2 rounded-full bg-canvas">
            <div
              className="h-2 rounded-full bg-indigo"
              style={{ width: `${done ? 100 : failed ? Math.max(15, current * 18) : Math.max(12, current * 18)}%` }}
            />
          </div>
          <div className="mt-6 divide-y divide-line">
            {steps.map((s, i) => {
              const completed = done || i < current;
              const active = !done && !failed && i === current;
              return (
                <div className="flex items-start gap-4 py-5" key={s}>
                  {completed ? (
                    <CheckCircle2 className="text-ok" />
                  ) : active ? (
                    <LoaderCircle className="animate-spin text-indigo" />
                  ) : (
                    <span className="h-6 w-6 rounded-full border-2 border-line" />
                  )}
                  <div className="flex-1">
                    <b className={active ? "text-ink" : completed ? "text-slate" : "text-slate"}>{s}</b>
                    {active && stage === "extracting" && state?.progress && (
                      <p className="text-body text-slate">
                        Reading part {state.progress.current} of {state.progress.total}
                      </p>
                    )}
                  </div>
                  <span className="text-body text-slate">
                    {completed ? "Completed" : active ? "In progress" : failed && i === current ? "Failed" : "Pending"}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
        {failed && (
          <div className="mt-4 rounded-card bg-bad-soft p-5 text-bad">
            <b>Analysis failed</b>
            <p>{state?.error?.message}</p>
            {state?.error?.code === "NO_EXTRACTABLE_TEXT" && (
              <p className="mt-2">This looks like a scanned document. OCR is not supported.</p>
            )}
            <Button className="mt-3" onClick={retryAnalysis}>
              Retry analysis
            </Button>
          </div>
        )}
        {done && (
          <Card className="mt-4 p-5">
            <h2 className="text-section">Analysis complete</h2>
            <p className="mt-2 text-body text-slate">
              {state.summary?.extracted_items ?? 0} extracted items · {state.summary?.obligations ?? 0} obligations ·{" "}
              {state.summary?.pending_reviews ?? 0} items need review · {state.summary?.open_clarifications ?? 0} open
              clarifications
            </p>
            <Link to={`/contracts/${id}`}>
              <Button variant="primary" className="mt-4">
                View results
              </Button>
            </Link>
          </Card>
        )}
        <p className="mt-6 text-body text-slate">
          Extracted information will need your review before it is added to the approved record.
        </p>
      </div>
    </>
  );
}
