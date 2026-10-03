import { useApi } from "@/lib/useApi";
import { api, resetWorkspace, workspaceId } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { PageHeader, Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { Async, TableSkeleton } from "@/components/ui/States";
const PROVIDER_LABEL = { ollama: "Ollama (local)", groq: "Groq (hosted)" };

export default function Settings() {
  const a = useApi(api.health);
  return (
    <>
      <PageHeader title="Settings" subtitle="API connection and service health." />
      <Async state={a} skeleton={<TableSkeleton />}>
        {(h) => (
          <div className="max-w-2xl space-y-4">
            <Card className="p-5">
              <b>API base URL</b>
              <p className="mt-2 text-body text-slate">
                {import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api"}
              </p>
            </Card>
            <Card className="space-y-4 p-5">
              <h2 className="text-section">Service health</h2>
              <p>
                Database{" "}
                <StatusBadge kind={h.database.toLowerCase() === "ok" ? "approved" : "rejected"} label={h.database} />
              </p>
              <p>
                AI service <b>{PROVIDER_LABEL[h.llm.provider] ?? h.llm.provider}</b>{" "}
                <StatusBadge
                  kind={h.llm.reachable ? "approved" : "rejected"}
                  label={h.llm.reachable ? "Reachable" : "Unavailable"}
                />
              </p>
              <p>
                Model <b>{h.llm.model}</b>
                {h.llm.provider !== h.llm.primary && (
                  <span className="text-slate">
                    {" "}
                    (fallback: {PROVIDER_LABEL[h.llm.primary] ?? h.llm.primary} is unavailable)
                  </span>
                )}
              </p>
              {h.llm.fallback && h.llm.provider === h.llm.primary && (
                <p className="text-slate">
                  Fallback if unavailable: {PROVIDER_LABEL[h.llm.fallback] ?? h.llm.fallback}
                </p>
              )}
              <p>
                Model available{" "}
                <StatusBadge
                  kind={h.llm.model_available ? "approved" : "rejected"}
                  label={h.llm.model_available ? "Available" : "Unavailable"}
                />
              </p>
            </Card>
            <Card className="space-y-3 p-5">
              <h2 className="text-section">Your workspace</h2>
              <p className="text-body text-slate">
                On the online demo, your uploads and review decisions are kept in a private workspace tied to this
                browser. Other visitors cannot see or change them. It starts with its own copy of the demo contracts.
              </p>
              <p className="font-mono text-meta text-slate">{workspaceId()}</p>
              <Button
                onClick={() => {
                  resetWorkspace();
                  window.location.assign("/dashboard");
                }}
              >
                Start a fresh workspace
              </Button>
            </Card>
          </div>
        )}
      </Async>
    </>
  );
}
