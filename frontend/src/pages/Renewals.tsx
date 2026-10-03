import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtDate, fmtDaysUntil, unitLabel } from "@/lib/format";
import type { ExtractedItem } from "@/lib/types";
import { PageHeader, Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { FilterSelect } from "@/components/ui/Select";
import { Async, TableSkeleton, EmptyState } from "@/components/ui/States";
import { CitationChip } from "@/components/ui/CitationChip";
type Period = "Next 12 months" | "Next 24 months" | "All";
type Filter = "All" | "Calculated" | "Needs review" | "Conflict";
export default function Renewals() {
  const a = useApi(api.renewals);
  const [period, P] = useState<Period>("Next 24 months"),
    [filter, F] = useState<Filter>("All"),
    [items, setItems] = useState<Record<string, ExtractedItem[]>>({});
  const requested = useRef(new Set<string>());
  const vals = a.data ?? [];
  const visible = vals.filter(
    (x) =>
      (period === "All" ||
        (x.days_until_term_end !== null && x.days_until_term_end <= (period === "Next 12 months" ? 365 : 730))) &&
      (filter === "All" ||
        (filter === "Calculated" && x.calculation_status === "calculated") ||
        (filter === "Needs review" && !x.inputs_reviewed) ||
        (filter === "Conflict" && x.calculation_status === "blocked_by_conflict")),
  );
  useEffect(() => {
    for (const x of a.data ?? [])
      if (!requested.current.has(x.contract_id) && requested.current.add(x.contract_id))
        api
          .extractedItems(x.contract_id)
          .then((v) => setItems((p) => ({ ...p, [x.contract_id]: v })))
          .catch(() => {});
  }, [a.data]);
  return (
    <>
      <PageHeader title="Renewals" subtitle="Review upcoming renewal dates and notice deadlines." />
      <div className="mb-6 flex gap-3">
        <FilterSelect
          label="Period"
          value={period}
          onChange={P}
          options={(["Next 12 months", "Next 24 months", "All"] as Period[]).map((value) => ({ value, label: value }))}
        />
        <FilterSelect
          label="Status"
          value={filter}
          onChange={F}
          options={(["All", "Calculated", "Needs review", "Conflict"] as Filter[]).map((value) => ({
            value,
            label: value,
          }))}
        />
      </div>
      <Async state={a} skeleton={<TableSkeleton />}>
        {() =>
          visible.length ? (
            <div className="space-y-5">
              {visible.map((x) => (
                <div className="grid grid-cols-[72px_1fr] gap-4" key={x.contract_id}>
                  <div className="border-r border-line pt-3 text-indigo">
                    <b className="block text-label">
                      {x.current_term_end
                        ? new Date(x.current_term_end + "T00:00:00Z")
                            .toLocaleString("en-US", { month: "short", timeZone: "UTC" })
                            .toUpperCase()
                        : "—"}
                    </b>
                    <strong className="text-page-title text-ink">{x.current_term_end?.slice(8, 10) ?? "—"}</strong>
                    <span className="block text-body text-slate">{x.current_term_end?.slice(0, 4)}</span>
                  </div>
                  <Card className="p-5">
                    <div className="flex flex-wrap justify-between gap-3">
                      <h2 className="text-section">{x.contract_name}</h2>
                      <div className="flex items-center gap-2 text-body text-slate">
                        {x.renewal_type === "automatic" ? "Renews" : "Expires"} {fmtDaysUntil(x.days_until_term_end)}
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
                    </div>
                    <div className="mt-5 grid gap-4 border-b border-line pb-5 sm:grid-cols-2 lg:grid-cols-4">
                      <div>
                        <small className="text-slate">Renewal type</small>
                        <p className="capitalize">{x.renewal_type ?? "—"}</p>
                      </div>
                      <div>
                        <small className="text-slate">Renewal period</small>
                        <p>{x.renewal_period ? unitLabel(x.renewal_period.value, x.renewal_period.unit) : "—"}</p>
                      </div>
                      <div>
                        <small className="text-slate">Notice period</small>
                        <p>
                          {x.notice_period
                            ? `${unitLabel(x.notice_period.value, x.notice_period.unit)}${x.notice_period.unit.includes("business") ? " business days" : ""}`
                            : "—"}
                        </p>
                      </div>
                      <div>
                        <small className="text-slate">Notice deadline</small>
                        {x.calculation_status !== "calculated" ? (
                          <p className="mt-1 rounded-control bg-warn-soft p-2 text-warn">
                            {x.calculation_note || "Calculation needs review"}
                            <Link className="ml-2 underline" to="/review">
                              Resolve in Review Queue →
                            </Link>
                          </p>
                        ) : (
                          <p
                            className={
                              x.days_until_notice_deadline !== null && x.days_until_notice_deadline < 0
                                ? "text-bad"
                                : x.days_until_notice_deadline !== null && x.days_until_notice_deadline <= 60
                                  ? "text-warn"
                                  : ""
                            }
                          >
                            {fmtDate(x.notice_deadline)}
                            {x.days_until_notice_deadline !== null
                              ? ` · ${x.days_until_notice_deadline < 0 ? `passed ${fmtDaysUntil(x.days_until_notice_deadline)}` : `${x.days_until_notice_deadline} days`}`
                              : ""}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-3">
                      <div className="flex flex-wrap gap-2">
                        {(items[x.contract_id] ?? [])
                          .filter((i) => i.field_name === "notice_period" && x.input_item_ids.includes(i.id))
                          .flatMap((i) => i.citations.slice(0, 1))
                          .map((c) => (
                            <CitationChip key={c.id} citation={c} />
                          ))}
                      </div>
                      <Link className="text-indigo" to={`/contracts/${x.contract_id}?tab=analysis`}>
                        Review renewal →
                      </Link>
                    </div>
                  </Card>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No renewals found" text="No renewals match the current filters." />
          )
        }
      </Async>
    </>
  );
}
