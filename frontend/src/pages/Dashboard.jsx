import { Link } from "react-router-dom";
import { useApi } from "@/lib/useApi";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PageHeader, SectionTitle, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { TableSkeleton, ErrorState, EmptyState } from "@/components/ui/States";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const d = useApi(api.dashboard),
    r = useApi(api.renewals),
    q = useApi(api.reviewQueue),
    c = useApi(() => api.clarifications({ status: "open" }));
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (d.data && r.data && q.data && c.data) setLoaded(true);
  }, [d.data, r.data, q.data, c.data]);
  const err = d.error ?? r.error ?? q.error ?? c.error;
  const retry = () => {
    d.reload();
    r.reload();
    q.reload();
    c.reload();
  };
  if (err && !loaded) return <ErrorState error={err} onRetry={retry} />;
  if (!d.data || !r.data || !q.data || !c.data) return <TableSkeleton />;
  const data = d.data;
  const renewals = r.data.filter(
    (x) => x.days_until_term_end !== null && x.days_until_term_end >= 0 && x.days_until_term_end <= 365,
  );
  const deadlines = data.upcoming_deadlines.filter((x) => x.type === "obligation");
  const clarifications = c.data;
  const queue = [...q.data]
    .sort((a, b) => ({ low: 0, medium: 1, high: 2 })[a.confidence] - { low: 0, medium: 1, high: 2 }[b.confidence])
    .slice(0, Math.max(0, 4 - clarifications.length));
  if (data.counts.contracts === 0)
    return (
      <>
        <PageHeader
          title="Dashboard"
          subtitle="Overview of your contracts, obligations, and upcoming renewals."
          actions={
            <Link to="/contracts/upload">
              <Button variant="primary">+ Upload Contract</Button>
            </Link>
          }
        />
        <EmptyState
          title="No contracts yet"
          text="Upload your first contract to start organizing extracted information."
          action={
            <Link to="/contracts/upload">
              <Button variant="primary">Upload Contract</Button>
            </Link>
          }
        />
      </>
    );
  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of your contracts, obligations, and upcoming renewals."
        actions={
          <Link to="/contracts/upload">
            <Button variant="primary">+ Upload Contract</Button>
          </Link>
        }
      />
      <div className="mb-8 grid grid-cols-2 overflow-hidden rounded-card border border-line md:grid-cols-4">
        {[
          ["Active Contracts", data.counts.contracts],
          ["Needs Review", data.counts.contracts_needing_review],
          ["Upcoming Obligations", deadlines.length],
          ["Upcoming Renewals", renewals.length],
        ].map(([a, b], i) => (
          <div key={String(a)} className="border-b border-r border-line p-5">
            <div className="text-body text-slate">{a}</div>
            <strong className="mt-1 block text-page-title">
              {b}
              {i === 1 && Number(b) > 0 && <i className="ml-3 inline-block h-2 w-2 rounded-full bg-warn" />}
            </strong>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <SectionTitle
            action={
              <Link className="text-body text-indigo hover:underline" to="/obligations">
                View all
              </Link>
            }
          >
            Upcoming Obligations
          </SectionTitle>
          <Card className="overflow-hidden">
            <table className="w-full text-left text-body">
              <thead className="bg-canvas text-slate">
                <tr>
                  {["Obligation", "Contract", "Due date", "Status"].map((x) => (
                    <th className="px-4 py-3 font-medium" key={x}>
                      {x}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deadlines.slice(0, 4).map((x) => (
                  <tr key={x.entity_id} className="border-t border-line hover:bg-indigo-soft">
                    <td className="px-4 py-4">
                      <Link to={`/obligations?selected=${x.entity_id}`} className="font-medium">
                        {x.label}
                      </Link>
                    </td>
                    <td className="px-4 py-4">{x.contract_name}</td>
                    <td className="px-4 py-4">{fmtDate(x.date)}</td>
                    <td className="px-4 py-4">
                      <StatusBadge kind={x.days_until < 0 ? "overdue" : "upcoming"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!deadlines.length && <p className="p-6 text-slate">No obligations found</p>}
          </Card>
        </section>
        <section className="lg:col-span-2">
          <SectionTitle
            action={
              <Link className="text-body text-indigo hover:underline" to="/renewals">
                View all
              </Link>
            }
          >
            Upcoming Renewals
          </SectionTitle>
          <Card className="divide-y divide-line px-4">
            {!renewals.length && <p className="py-6 text-body text-slate">No renewals in the next 12 months</p>}
            {renewals.slice(0, 4).map((x) => (
              <div key={x.contract_id} className="py-4">
                <div className="flex justify-between gap-2 font-medium">
                  {x.contract_name}
                  <StatusBadge
                    kind={
                      x.calculation_status === "blocked_by_conflict"
                        ? "conflict"
                        : !x.inputs_reviewed
                          ? "needs_review"
                          : "approved"
                    }
                  />
                </div>
                <p className="mt-1 text-body text-slate">
                  {x.renewal_type === "automatic" ? "Renews" : "Expires"} {fmtDate(x.current_term_end)} ·{" "}
                  {x.days_until_term_end} days
                </p>
              </div>
            ))}
          </Card>
        </section>
      </div>
      <section className="mt-8">
        <SectionTitle
          action={
            <Link className="text-body text-indigo hover:underline" to="/review">
              Open Review Queue
            </Link>
          }
        >
          Needs Review
        </SectionTitle>
        <Card className="divide-y divide-line">
          {clarifications.slice(0, 4).map((item) => (
            <div className="flex flex-wrap items-center gap-4 px-5 py-4" key={item.id}>
              <span className="flex-1 font-medium">
                {item.kind === "conflict"
                  ? `Conflicting ${(item.field_name ?? "information").replace(/_/g, " ")}s`
                  : item.kind === "missing"
                    ? "Missing expiration date"
                    : `Ambiguous ${(item.field_name ?? "clause").replace(/_/g, " ")}`}
              </span>
              <span className="text-slate">
                {item.contract_name} ·{" "}
                {item.citations[0]
                  ? `${item.citations[0].section ?? "Source"}${item.citations[0].page ? ` · Page ${item.citations[0].page}` : ""}`
                  : "No source"}
              </span>
              <StatusBadge kind={item.kind === "conflict" ? "conflict" : "clarification"} />
              <Link className="text-indigo" to="/review">
                Review
              </Link>
            </div>
          ))}
          {clarifications.length < 4 &&
            queue.map((item) => (
              <div className="flex flex-wrap items-center gap-4 px-5 py-4" key={item.entity_id}>
                <span className="flex-1 font-medium">
                  {item.confidence === "low" ? `Low-confidence ${item.label.toLowerCase()}` : item.label}
                </span>
                <span className="text-slate">{item.contract_name}</span>
                <StatusBadge kind="needs_review" />
                <Link className="text-indigo" to={`/review/${item.entity_type}/${item.entity_id}`}>
                  Review
                </Link>
              </div>
            ))}
        </Card>
      </section>
    </>
  );
}
