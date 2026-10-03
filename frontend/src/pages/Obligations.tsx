import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader } from "@/components/ui/Card";
import { PillTabs } from "@/components/ui/Tabs";
import ObligationTable from "@/components/obligations/ObligationTable";
import ObligationDetail from "@/components/obligations/ObligationDetail";
import { Async, TableSkeleton, EmptyState } from "@/components/ui/States";
type Tab = "All" | "Upcoming" | "Needs Review" | "Approved" | "Rejected";
export default function Obligations() {
  const a = useApi(api.obligations);
  const rejected = useApi(() => api.obligations({ review_status: "rejected" }));
  const [tab, T] = useState<Tab>("All");
  const [params, setParams] = useSearchParams();
  const all = a.data ?? [];
  const rejectedItems = rejected.data ?? [];
  const approved = all.filter((o) => o.review_status === "approved" || o.review_status === "edited");
  const filtered =
    tab === "Rejected"
      ? rejectedItems
      : tab === "Upcoming"
        ? all.filter(
            (o) => o.status === "open" && o.days_until_due !== null && o.days_until_due >= 0 && o.days_until_due <= 60,
          )
        : tab === "Needs Review"
          ? all.filter((o) => o.review_status === "pending")
          : tab === "Approved"
            ? approved
            : all;
  const selected = filtered.find((o) => o.id === params.get("selected")) ?? filtered[0];
  const counts = [
    all.length,
    all.filter(
      (o) => o.status === "open" && o.days_until_due !== null && o.days_until_due >= 0 && o.days_until_due <= 60,
    ).length,
    all.filter((o) => o.review_status === "pending").length,
    approved.length,
    rejectedItems.length,
  ];
  return (
    <>
      <PageHeader title="Obligations" subtitle="Track obligations and deadlines extracted from your contracts." />
      <Async state={a} skeleton={<TableSkeleton />}>
        {() => (
          <>
            <PillTabs
              tabs={(["All", "Upcoming", "Needs Review", "Approved", "Rejected"] as Tab[]).map((key, i) => ({
                key,
                label: key,
                count: counts[i],
              }))}
              value={tab}
              onChange={T}
            />
            {filtered.length ? (
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,1fr)]">
                <ObligationTable
                  items={filtered}
                  selected={selected?.id}
                  onSelect={(o) => setParams({ selected: o.id })}
                />
                {selected && (
                  <ObligationDetail
                    item={selected}
                    onReviewed={() => {
                      a.reload();
                      rejected.reload();
                    }}
                    onStatus={async (s) => {
                      await api.setObligationStatus(selected.id, s);
                      a.reload();
                    }}
                  />
                )}
              </div>
            ) : (
              <EmptyState title="No obligations found" text="No obligations match the current filters." />
            )}
          </>
        )}
      </Async>
    </>
  );
}
