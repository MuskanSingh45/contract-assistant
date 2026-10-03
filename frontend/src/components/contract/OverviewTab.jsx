import { History } from "lucide-react";

import { api } from "@/lib/api";

import { fmtDaysUntil, fmtLongDate, reviewStatusKind, unitLabel } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { StatusBadge } from "@/components/ui/Badge";
import { Card, SectionTitle } from "@/components/ui/Card";
import { CitationChip } from "@/components/ui/CitationChip";
import { Skeleton } from "@/components/ui/States";

function KeyDate({ label, value, sub, item, badge }) {
  return (
    <div className="flex min-h-[200px] flex-col p-6">
      <span className="text-body text-slate">{label}</span>
      <span className="mt-2 text-value text-ink">{value}</span>
      <div className="mt-3">
        {badge ??
          (item ? (
            <StatusBadge
              kind={
                item.review_status === "approved"
                  ? "confirmed"
                  : reviewStatusKind(item.review_status, { conflict: item.in_open_clarification })
              }
            />
          ) : null)}
      </div>
      {sub && <div className="mt-3 text-body text-slate">{sub}</div>}
      <div className="mt-auto pt-4">{item?.citations[0] && <CitationChip citation={item.citations[0]} />}</div>
    </div>
  );
}

function Row({ label, n, tone }) {
  return (
    <div className="flex justify-between text-body">
      <span className="text-slate">{label}</span>
      <span className={tone ?? "text-ink"}>{n}</span>
    </div>
  );
}

export default function OverviewTab({ contract }) {
  const versionId = contract.version.id;
  const state = useApi(
    () =>
      Promise.all([
        api.extractedItems(contract.id, versionId),
        api.obligations({ contract_id: contract.id, version_id: versionId }),
        contract.version.version_number > 1 && contract.version.analysis_status === "completed"
          ? api.versionChanges(contract.id, versionId).catch(() => null)
          : Promise.resolve(null),
      ]),
    [contract.id, versionId, contract.updated_at],
  );

  if (!state.data) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-44 rounded-card" />
        ))}
      </div>
    );
  }
  const [items, obligations, changes] = state.data;
  const pick = (f) =>
    items.find((i) => i.field_name === f && i.review_status !== "rejected" && !i.in_open_clarification) ??
    items.find((i) => i.field_name === f && i.review_status !== "rejected");
  const r = contract.renewal;
  const blocked = r?.calculation_status === "blocked_by_conflict";
  const notice = pick("notice_period");
  const renewalItem = pick("renewal_terms");

  const all = [...items, ...obligations];
  const approved = all.filter((i) => i.review_status === "approved" || i.review_status === "edited").length;
  const pending = all.filter((i) => i.review_status === "pending").length;
  const edited = all.filter((i) => i.review_status === "edited").length;
  const rejected = all.filter((i) => i.review_status === "rejected").length;
  const stale = (changes?.items ?? []).filter(
    (c) => c.previous_review_status === "approved" || c.previous_review_status === "edited",
  );

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <div>
        <SectionTitle>Key dates</SectionTitle>
        <Card className="grid divide-line md:grid-cols-2 [&>*:nth-child(-n+2)]:border-b [&>*:nth-child(odd)]:md:border-r">
          <KeyDate label="Effective Date" value={fmtLongDate(r?.effective_date)} item={pick("effective_date")} />
          <KeyDate
            label="Expiration Date"
            value={fmtLongDate(r?.expiration_date)}
            item={pick("expiration_date") ?? pick("initial_term")}
            sub={
              r?.expiration_source === "calculated"
                ? "Calculated from effective date + initial term"
                : r?.current_term_end && r.current_term_end !== r.expiration_date
                  ? `Auto-renewed · current term ends ${fmtLongDate(r.current_term_end)}`
                  : undefined
            }
          />
          <KeyDate
            label="Notice Deadline"
            value={blocked ? "Needs clarification" : fmtLongDate(r?.notice_deadline)}
            item={notice}
            badge={blocked ? <StatusBadge kind="conflict" /> : undefined}
            sub={
              blocked || r?.calculation_status === "incomplete" ? (
                <span className="text-warn">{r?.calculation_note}</span>
              ) : r?.notice_period ? (
                <>
                  {unitLabel(r.notice_period.value, r.notice_period.unit)} before{" "}
                  {r.notice_period.anchor === "renewal_date" ? "renewal" : "expiration"}
                  {r.days_until_notice_deadline !== null && (
                    <span
                      className={
                        r.days_until_notice_deadline < 0
                          ? "text-bad"
                          : r.days_until_notice_deadline <= 60
                            ? "text-warn"
                            : ""
                      }
                    >
                      {" "}
                      ·{" "}
                      {r.days_until_notice_deadline < 0
                        ? `passed ${fmtDaysUntil(r.days_until_notice_deadline)}`
                        : `${r.days_until_notice_deadline} days left`}
                    </span>
                  )}
                  {!r.inputs_reviewed && <span className="block text-meta">Based on unreviewed data</span>}
                </>
              ) : (
                "No notice period found in the document"
              )
            }
          />
          <KeyDate
            label="Renewal"
            value={
              r?.renewal_type === "automatic"
                ? "Automatic renewal"
                : r?.renewal_type === "optional"
                  ? "Optional renewal"
                  : r?.renewal_type === "none"
                    ? "No renewal"
                    : "Not found"
            }
            item={renewalItem}
            sub={
              r?.renewal_period
                ? `Successive ${unitLabel(r.renewal_period.value, r.renewal_period.unit).replace(/s$/, "")} periods`
                : undefined
            }
          />
        </Card>
        <p className="mt-3 text-table text-slate">
          Dates are calculated by the application from the extracted rules, never by the AI. Citation chips open the
          source.
        </p>
      </div>

      <div className="space-y-8">
        <div>
          <SectionTitle>Parties</SectionTitle>
          <Card className="space-y-4 p-5">
            {contract.parties.length === 0 && <p className="text-body text-slate">No parties found.</p>}
            {contract.parties.map((p) => {
              const item = items.find((i) => i.id === p.item_id);
              return (
                <div key={p.item_id}>
                  <p className="text-body font-medium text-ink">{p.name}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-2 text-table text-slate">
                    <span className="capitalize">{p.role ?? "Role not stated"}</span>
                    {item?.citations[0] && <CitationChip citation={item.citations[0]} className="!px-1.5 !py-0" />}
                  </p>
                </div>
              );
            })}
          </Card>
        </div>
        <div>
          <SectionTitle>Review progress</SectionTitle>
          <Card className="space-y-3 p-5">
            <div className="flex justify-between text-body">
              <span className="text-slate">{all.length} extracted items</span>
              <span className="font-semibold text-ink">{approved} approved</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-line">
              <div
                className="h-full rounded-full bg-ok"
                style={{ width: `${all.length ? (approved / all.length) * 100 : 0}%` }}
              />
            </div>
            <Row label="Needs review" n={pending} tone={pending ? "text-warn" : undefined} />
            <Row
              label="Open clarifications"
              n={contract.counts.open_clarifications}
              tone={contract.counts.open_clarifications ? "text-bad" : undefined}
            />
            <Row label="Edited · Rejected" n={`${edited} · ${rejected}`} />
          </Card>
        </div>
        {stale.length > 0 && (
          <div className="flex gap-3 rounded-card border border-amber-300 bg-warn-soft p-4">
            <History className="mt-0.5 h-4 w-4 shrink-0 text-warn" />
            <div>
              <p className="text-body font-semibold text-warn">
                {stale.length} {stale.length === 1 ? "item" : "items"} may be stale
              </p>
              <p className="text-table text-warn">
                Version {contract.version.version_number} differs from values approved in version{" "}
                {contract.version.version_number - 1}. See the Versions tab.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
