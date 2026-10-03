import { useState } from "react";
import { api } from "@/lib/api";

import { useApi } from "@/lib/useApi";
import { PillTabs } from "@/components/ui/Tabs";
import { Card } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/States";
import { ExtractionItemCard } from "@/components/review/ExtractionItemCard";
import { ClarificationCard } from "@/components/review/ClarificationCard";

const groups = {
  all: [
    "party",
    "effective_date",
    "expiration_date",
    "initial_term",
    "renewal_terms",
    "notice_period",
    "termination_clause",
  ],
  parties: ["party"],
  dates: ["effective_date", "expiration_date", "initial_term"],
  renewal: ["renewal_terms", "notice_period", "termination_clause"],
};

const labels = {
  party: "Parties",
  effective_date: "Effective date",
  expiration_date: "Expiration date",
  renewal_terms: "Renewal terms",
  notice_period: "Notice period",
};

function NotFound({ field }) {
  return (
    <Card className="border-dashed p-5">
      <p className="text-body text-slate">{labels[field]}</p>
      <p className="mt-1 text-body text-ink">Not found in document</p>
      <p className="mt-1 text-table text-slate">
        The AI found no supported statement for this field. Nothing was guessed.
      </p>
    </Card>
  );
}

export default function AnalysisTab({ contract, onChanged }) {
  const [group, setGroup] = useState("all");
  const items = useApi(() => api.extractedItems(contract.id, contract.version.id), [contract.id, contract.version.id]);
  const clarifications = useApi(
    () => api.clarifications({ contract_id: contract.id }),
    [contract.id, contract.version.id],
  );

  const refresh = () => {
    items.reload();
    clarifications.reload();
    onChanged();
  };

  if (!items.data)
    return (
      <div className="space-y-4">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-36 rounded-card" />
        ))}
      </div>
    );
  const list = items.data;
  const openQ = (clarifications.data ?? []).filter(
    (c) => c.status === "open" && c.contract_version_id === contract.version.id,
  );
  const closedQ = (clarifications.data ?? []).filter(
    (c) => c.status !== "open" && c.contract_version_id === contract.version.id,
  );
  const count = (fields) => list.filter((i) => fields.includes(i.field_name)).length;

  const visible = group === "conflicts" ? [] : list.filter((i) => groups[group].includes(i.field_name));
  const missing =
    group === "conflicts"
      ? []
      : ["party", "effective_date", "expiration_date", "renewal_terms", "notice_period"].filter(
          (f) =>
            groups[group].includes(f) &&
            !list.some((i) => i.field_name === f) &&
            !(f === "expiration_date" && list.some((i) => i.field_name === "initial_term")),
        );

  return (
    <div>
      <PillTabs
        value={group}
        onChange={setGroup}
        tabs={[
          { key: "all", label: "All", count: list.length },
          { key: "parties", label: "Parties", count: count(groups.parties) },
          { key: "dates", label: "Dates", count: count(groups.dates) },
          { key: "renewal", label: "Renewal & Termination", count: count(groups.renewal) },
          { key: "conflicts", label: "Conflicts & Questions", count: openQ.length },
        ]}
      />

      {group === "conflicts" ? (
        <div className="space-y-4">
          {openQ.length === 0 && closedQ.length === 0 && (
            <EmptyState
              icon="check"
              title="No conflicts or questions"
              text="Nothing in this contract needs clarification."
            />
          )}
          {openQ.map((c) => (
            <ClarificationCard key={c.id} clarification={c} onResolved={refresh} />
          ))}
          {closedQ.map((c) => (
            <ClarificationCard key={c.id} clarification={c} onResolved={refresh} />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {openQ.length > 0 && group === "all" && (
            <button
              onClick={() => setGroup("conflicts")}
              className="w-full rounded-card border border-bad/20 bg-bad-soft px-5 py-3 text-left text-body text-bad hover:border-bad/40"
            >
              {openQ.length} {openQ.length === 1 ? "question needs" : "questions need"} your decision before all
              deadlines can be calculated →
            </button>
          )}
          {visible.map((item) => (
            <ExtractionItemCard key={item.id} item={item} onReviewed={refresh} />
          ))}
          {missing.map((f) => (
            <NotFound key={f} field={f} />
          ))}
          {visible.length === 0 && missing.length === 0 && (
            <EmptyState title="Nothing extracted" text="No information of this type was found in the document." />
          )}
        </div>
      )}
    </div>
  );
}
