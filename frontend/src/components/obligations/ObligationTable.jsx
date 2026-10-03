import { fmtDate } from "@/lib/format";
import { StatusBadge } from "@/components/ui/Badge";
export function obligationKind(o) {
  if (o.review_status === "rejected") return "rejected";
  if (o.status === "completed") return "completed";
  if (o.days_until_due !== null && o.days_until_due < 0 && o.status === "open") return "overdue";
  if (o.review_status === "pending") return "needs_review";
  if (o.days_until_due !== null && o.days_until_due >= 0 && o.days_until_due <= 60) return "upcoming";
  return o.review_status === "edited" ? "edited" : "approved";
}
export default function ObligationTable({ items, selected, onSelect }) {
  return (
    <div className="overflow-x-auto rounded-card border border-line">
      <table className="w-full min-w-[560px] text-left text-body">
        <thead className="bg-canvas text-slate">
          <tr>
            {["Obligation", "Responsible Party", "Due", "Status"].map((h) => (
              <th key={h} className="px-4 py-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((o) => (
            <tr
              onClick={() => onSelect(o)}
              key={o.id}
              className={`cursor-pointer border-t border-line ${selected === o.id ? "bg-indigo-soft" : "hover:bg-canvas"}`}
            >
              <td className="px-4 py-4">
                <b>{o.description}</b>
                <small className="block text-slate">{o.contract_name}</small>
              </td>
              <td className="px-4 py-4">{o.responsible_party ?? "—"}</td>
              <td title={!o.due_date ? (o.frequency_text ?? undefined) : undefined} className="px-4 py-4">
                {fmtDate(o.due_date)}
              </td>
              <td className="whitespace-nowrap px-4 py-4">
                <StatusBadge kind={obligationKind(o)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
