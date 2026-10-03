import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtDate } from "@/lib/format";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useSource } from "@/components/SourceDrawer";
import { Async, TableSkeleton, EmptyState } from "@/components/ui/States";
export default function SummaryTab({ contractId, versionId }) {
  const d = useApi(() => api.getContract(contractId, versionId), [contractId, versionId]);
  const i = useApi(() => api.extractedItems(contractId, versionId), [contractId, versionId]);
  const o = useApi(() => api.obligations({ contract_id: contractId, version_id: versionId }), [contractId, versionId]);
  const c = useApi(() => api.clarifications({ contract_id: contractId, status: "open" }), [contractId]);
  const { open } = useSource();
  if (d.loading || i.loading || o.loading || c.loading) return <TableSkeleton />;
  if (d.error) return <Async state={d}>{() => null}</Async>;
  if (!d.data || !i.data || !o.data || !c.data) return <EmptyState title="Unable to load summary" text="Try again." />;
  const con = d.data,
    items = i.data,
    obs = o.data,
    clar = c.data;
  const approvedItems = items.filter((x) => x.review_status === "approved" || x.review_status === "edited"),
    approvedObs = obs.filter((x) => x.review_status === "approved" || x.review_status === "edited");
  const approved = approvedItems.length + approvedObs.length,
    total = items.length + obs.length;
  // Facts: approved/edited first; pending shown with an "unreviewed" tag; rejected never shown.
  const usable = (x) => x.review_status !== "rejected";
  const find = (field) =>
    approvedItems.find((x) => x.field_name === field) ??
    items.find((x) => x.field_name === field && usable(x) && !x.in_open_clarification);
  const tag = (x) => (x && x.review_status === "pending" ? "  (unreviewed)" : "");
  const term = find("effective_date"),
    expiry = find("expiration_date"),
    renew = find("renewal_terms");
  const attention = items
    .filter((x) => x.review_status === "pending")
    .map((x) => ({ label: `${x.label}: ${x.display_value} needs review`, c: x.citations[0] }))
    .concat(clar.map((x) => ({ label: x.question, c: x.citations[0] })));
  const rows = [
    { label: "Contract", value: con.name, c: items[0]?.citations[0] },
    {
      label: "Parties",
      value:
        con.parties
          .filter((x) => x.review_status === "approved" || x.review_status === "edited")
          .map((x) => x.name)
          .join("\n") || "—",
      c: items.find((x) => x.field_name === "party")?.citations[0],
    },
    {
      label: "Term",
      value: `Effective date: ${term?.display_value ?? "—"}${tag(term)}\nExpiration: ${expiry?.display_value ?? "—"}${tag(expiry)}`,
      c: term?.citations[0] ?? expiry?.citations[0],
    },
    { label: "Renewal", value: renew ? `${renew.display_value}${tag(renew)}` : "—", c: renew?.citations[0] },
    {
      label: "Key Obligations",
      value:
        obs
          .filter(usable)
          .map((x) => `• ${x.description}${tag(x)}`)
          .join("\n") || "—",
      c: obs.filter(usable)[0]?.citations[0],
    },
    {
      label: "Important Dates",
      value:
        obs
          .filter((x) => usable(x) && x.due_date)
          .map((x) => [x.due_date, `${x.description}${tag(x)}`])
          .concat(con.renewal?.notice_deadline ? [[con.renewal.notice_deadline, "Notice deadline"]] : [])
          .concat(con.renewal?.current_term_end ? [[con.renewal.current_term_end, "Contract term ends"]] : [])
          .sort((a, b) => a[0].localeCompare(b[0]))
          .map(([d, l]) => `${fmtDate(d)}  ·  ${l}`)
          .join("\n") || "—",
      c: obs[0]?.citations[0],
    },
    {
      label: "Items Requiring Attention",
      value:
        attention
          .slice(0, 6)
          .map((x) => `• ${x.label}`)
          .concat(attention.length > 6 ? [`…and ${attention.length - 6} more in the Review Queue`] : [])
          .join("\n") || "None",
      c: attention[0]?.c,
    },
  ];
  return (
    <>
      <div className="flex justify-end print:hidden">
        <Button onClick={() => window.print()}>Print</Button>
      </div>
      <Card className="mx-auto mt-4 max-w-4xl border-line p-10 shadow-sm">
        <p className="text-label text-slate">REVIEWED SUMMARY</p>
        <h1 className="mt-3 text-2xl font-semibold">{con.name}</h1>
        <p className="mt-2 text-body text-slate">
          Version {con.version.version_number} · {approved} of {total} items approved
        </p>
        <div className="mt-8">
          {rows.map((row) => (
            <div key={row.label} className="grid grid-cols-[180px_1fr_100px] gap-4 border-t border-line py-5">
              <b>{row.label}</b>
              <p className="whitespace-pre-line text-slate">{row.value}</p>
              {row.c && (
                <button className="text-indigo" onClick={() => open(row.c.id)}>
                  View source
                </button>
              )}
            </div>
          ))}
        </div>
        <p className="border-t border-line pt-5 text-meta text-slate">
          Reviewed information is based on the uploaded contract and user review. This tool does not provide legal
          advice.
        </p>
      </Card>
    </>
  );
}
