import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import type { QueueItem, RecentReview } from "@/lib/types";
import { fmtDateTime, reviewStatusKind } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader, SectionTitle } from "@/components/ui/Card";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { CitationChip } from "@/components/ui/CitationChip";
import { FilterSelect } from "@/components/ui/Select";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/States";
import { ClarificationCard } from "@/components/review/ClarificationCard";

type Reason = "all" | "conflict" | "unverified" | "ambiguous" | "low" | "other";

const confidenceRank = { low: 0, medium: 1, high: 2 };

/** Why this item is in the queue, most important first. */
function reasonOf(i: QueueItem): { key: Exclude<Reason, "all">; text: string } {
  if (i.clarification_id) return { key: "conflict", text: "Part of an open conflict or question" };
  if (i.citations.some((c) => c.validation_status === "not_found"))
    return { key: "unverified", text: "Quoted text not found in the document" };
  if (i.ambiguity_note) return { key: "ambiguous", text: i.ambiguity_note };
  if (i.confidence === "low") return { key: "low", text: "Low AI confidence" };
  return { key: "other", text: "New extraction awaiting review" };
}

const reasonBadge = {
  conflict: <StatusBadge kind="conflict" />,
  unverified: <StatusBadge kind="needs_review" label="Unverified source" />,
  ambiguous: <StatusBadge kind="clarification" label="Ambiguous wording" />,
  low: <StatusBadge kind="needs_review" />,
  other: <StatusBadge kind="needs_review" />,
};

const verb = { approve: "Approved", edit: "Edited", reject: "Rejected" };

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [contract, setContract] = useState("all");
  const [reason, setReason] = useState<Reason>("all");
  const [sort, setSort] = useState<"confidence" | "contract">("confidence");
  const queue = useApi(() => api.reviewQueue(), []);
  const questions = useApi(() => api.clarifications({ status: "open" }), []);
  const recent = useApi(() => api.recentReviews(8), []);

  const reload = () => {
    queue.reload();
    questions.reload();
    recent.reload();
  };

  const contracts = useMemo(() => {
    const m = new Map<string, string>();
    for (const i of queue.data ?? []) m.set(i.contract_id, i.contract_name);
    for (const q of questions.data ?? []) m.set(q.contract_id, q.contract_name);
    return [...m.entries()];
  }, [queue.data, questions.data]);

  const items = useMemo(() => {
    const list = (queue.data ?? []).filter(
      (i) => (contract === "all" || i.contract_id === contract) && (reason === "all" || reasonOf(i).key === reason),
    );
    return [...list].sort((a, b) =>
      sort === "confidence"
        ? confidenceRank[a.confidence] - confidenceRank[b.confidence] || a.contract_name.localeCompare(b.contract_name)
        : a.contract_name.localeCompare(b.contract_name),
    );
  }, [queue.data, contract, reason, sort]);

  const openQuestions = (questions.data ?? []).filter((q) => contract === "all" || q.contract_id === contract);
  const total = items.length + openQuestions.length;

  return (
    <>
      <PageHeader
        title="Review Queue"
        subtitle="Review extracted information before it becomes part of your approved contract record."
        actions={
          <Button
            variant="primary"
            disabled={!items.length}
            onClick={() =>
              navigate(`/review/${items[0].entity_type}/${items[0].entity_id}`, {
                state: { queue: items.map((i) => [i.entity_type, i.entity_id]) },
              })
            }
          >
            Start reviewing ({items.length})
          </Button>
        }
      />
      <div className="mb-6 flex flex-wrap gap-3">
        <FilterSelect
          label="Contract"
          value={contract}
          onChange={setContract}
          options={[
            { value: "all", label: "All contracts" },
            ...contracts.map(([id, name]) => ({ value: id, label: name })),
          ]}
        />
        <FilterSelect<Reason>
          label="Reason"
          value={reason}
          onChange={setReason}
          options={[
            { value: "all", label: "All" },
            { value: "conflict", label: "Conflicts" },
            { value: "unverified", label: "Unverified source" },
            { value: "ambiguous", label: "Ambiguous" },
            { value: "low", label: "Low confidence" },
            { value: "other", label: "Other" },
          ]}
        />
        <FilterSelect
          label="Sort"
          value={sort}
          onChange={setSort}
          options={[
            { value: "confidence", label: "Lowest confidence" },
            { value: "contract", label: "Contract" },
          ]}
        />
      </div>

      {openQuestions.length > 0 && (reason === "all" || reason === "conflict") && (
        <section className="mb-10">
          <SectionTitle count={openQuestions.length}>Clarification questions</SectionTitle>
          <div className="space-y-4">
            {openQuestions.map((q) => (
              <ClarificationCard key={q.id} clarification={q} showContract onResolved={reload} />
            ))}
          </div>
        </section>
      )}

      <section className="mb-10">
        <SectionTitle count={items.length}>Needs Review</SectionTitle>
        {queue.error ? (
          <ErrorState error={queue.error} onRetry={queue.reload} />
        ) : !queue.data ? (
          <TableSkeleton />
        ) : total === 0 ? (
          <EmptyState
            icon="check"
            title="You're all caught up"
            text="There are no extracted items currently waiting for review."
            action={<Button onClick={() => navigate("/dashboard")}>Go to Dashboard</Button>}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon="filter"
            title="No items match"
            text="No review items match the current filters."
            action={
              <Button
                onClick={() => {
                  setContract("all");
                  setReason("all");
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <Card className="overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-canvas text-table text-slate">
                <tr>
                  <th className="px-6 py-3 font-normal">Item · Contract</th>
                  <th className="px-4 py-3 font-normal">Extracted value</th>
                  <th className="px-4 py-3 font-normal">Reason for review</th>
                  <th className="px-4 py-3 font-normal">Confidence</th>
                  <th className="px-4 py-3 font-normal">Source</th>
                  <th className="px-4 py-3 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => {
                  const r = reasonOf(i);
                  return (
                    <tr
                      key={i.entity_id}
                      onClick={() =>
                        navigate(`/review/${i.entity_type}/${i.entity_id}`, {
                          state: { queue: items.map((x) => [x.entity_type, x.entity_id]) },
                        })
                      }
                      className="cursor-pointer border-t border-line align-top hover:bg-indigo-soft/40"
                    >
                      <td className="px-6 py-4">
                        <p className="text-body font-medium text-ink">{i.label}</p>
                        <p className="text-table text-slate">{i.contract_name}</p>
                      </td>
                      <td className="max-w-[220px] px-4 py-4 text-body text-ink">{i.display_value}</td>
                      <td className="max-w-[240px] px-4 py-4 text-body text-slate">{r.text}</td>
                      <td className="px-4 py-4">
                        <ConfidenceBadge level={i.confidence} short />
                      </td>
                      <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                        {i.citations[0] ? (
                          <CitationChip citation={i.citations[0]} />
                        ) : (
                          <span className="text-table text-slate">—</span>
                        )}
                      </td>
                      <td className="px-4 py-4">{reasonBadge[r.key]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}
      </section>

      <section>
        <SectionTitle count={recent.data?.length ?? 0}>Recently reviewed</SectionTitle>
        {recent.data && recent.data.length > 0 ? (
          <Card className="divide-y divide-line">
            {recent.data.map((r: RecentReview) => (
              <div key={r.id} className="flex flex-wrap items-center gap-4 px-6 py-4">
                <p className="min-w-[280px] flex-1 text-body text-ink">
                  <span className="font-medium">{r.label}</span> <span className="text-slate">· {r.contract_name}</span>
                </p>
                <p className="min-w-[220px] text-body text-slate">
                  {verb[r.action]}
                  {r.clarification_id ? " via clarification" : ""} · {fmtDateTime(r.reviewed_at)}
                </p>
                <StatusBadge kind={reviewStatusKind(r.new_review_status)} />
                <Link
                  to={`/review/${r.entity_type}/${r.entity_id}`}
                  className="w-12 text-right text-body text-slate hover:text-indigo"
                >
                  View
                </Link>
              </div>
            ))}
          </Card>
        ) : (
          <p className="text-body text-slate">No review actions yet.</p>
        )}
      </section>
    </>
  );
}
