import { PageHeader, Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
export default function Help() {
  return (
    <>
      <PageHeader title="Help / About" subtitle="How Contract Assistant organizes and reviews contract information." />
      <Card className="max-w-3xl space-y-6 p-6">
        <section>
          <h2 className="text-section">What this tool does</h2>
          <p className="mt-2 text-body text-slate">
            Contract Assistant extracts key dates, obligations, renewal terms, and other important information from
            uploaded contracts, then keeps those details organized for review.
          </p>
        </section>
        <section>
          <h2 className="text-section">How analysis works</h2>
          <p className="mt-2 text-body text-slate">
            AI extracts information from the contract. Code validates citations, detects conflicts, and calculates
            deadlines. You review the results before they become approved information.
          </p>
        </section>
        <section>
          <h2 className="text-section">Status badges</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {["approved", "needs_review", "conflict", "stale", "upcoming", "rejected"].map((x) => (
              <StatusBadge
                key={x}
                kind={x as "approved" | "needs_review" | "conflict" | "stale" | "upcoming" | "rejected"}
              />
            ))}
          </div>
          <p className="mt-2 text-body text-slate">
            Confidence describes how certain the AI is. Review status records your decision. Obligation status tracks
            whether work is open, completed, or not applicable.
          </p>
        </section>
        <p className="border-t border-line pt-4 text-body text-slate">This tool does not provide legal advice.</p>
      </Card>
    </>
  );
}
