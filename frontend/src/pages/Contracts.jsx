import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtDate } from "@/lib/format";

import { PageHeader, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { SearchInput, FilterSelect } from "@/components/ui/Select";
import { Async, EmptyState, TableSkeleton } from "@/components/ui/States";

function contractStatus(c) {
  const s = c.latest_version?.analysis_status;
  if (s === "processing" || s === "queued") return { kind: "neutral", label: "Analyzing" };
  if (s === "failed") return { kind: "rejected", label: "Analysis failed" };
  if (s === "not_started") return { kind: "neutral", label: "Not analyzed" };
  if (c.open_clarification_count > 0) return { kind: "conflict", label: "Potential Conflict" };
  if (c.pending_review_count > 0) return { kind: "needs_review", label: "Needs Review" };
  return { kind: "approved", label: "Approved" };
}
export default function Contracts() {
  const state = useApi(api.listContracts);
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [sort, setSort] = useState("Last updated");
  return (
    <>
      <PageHeader
        title="Contracts"
        subtitle="Manage uploaded contracts and review their extracted information."
        actions={
          <Link to="/contracts/upload">
            <Button variant="primary">+ Upload Contract</Button>
          </Link>
        }
      />
      <Async state={state} skeleton={<TableSkeleton />}>
        {(data) => {
          const all = data;
          let rows = all
            .filter((c) => (c.name + " " + c.parties.join(" ")).toLowerCase().includes(search.toLowerCase()))
            .filter((c) => {
              const s = contractStatus(c).label;
              return (
                filter === "All" ||
                (filter === "Needs review" && (c.pending_review_count > 0 || c.open_clarification_count > 0)) ||
                (filter === "Approved" && s === "Approved") ||
                (filter === "Analyzing" && s === "Analyzing") ||
                (filter === "Failed" && s === "Analysis failed")
              );
            });
          rows = [...rows].sort((a, b) =>
            sort === "Name"
              ? a.name.localeCompare(b.name)
              : sort === "Expiry"
                ? (a.current_term_end ?? "9999").localeCompare(b.current_term_end ?? "9999")
                : b.updated_at.localeCompare(a.updated_at),
          );
          return (
            <>
              <div className="mb-5 flex flex-wrap items-center gap-3">
                <SearchInput value={search} onChange={setSearch} placeholder="Search contracts" />
                <FilterSelect
                  label="Status"
                  value={filter}
                  onChange={setFilter}
                  options={["All", "Needs review", "Approved", "Analyzing", "Failed"].map((value) => ({
                    value,
                    label: value,
                  }))}
                />
                <FilterSelect
                  label="Sort"
                  value={sort}
                  onChange={setSort}
                  options={["Last updated", "Name", "Expiry"].map((value) => ({ value, label: value }))}
                />
                <span className="ml-auto text-body text-slate">
                  {rows.length} of {all.length} contracts
                </span>
              </div>
              {!all.length ? (
                <EmptyState
                  title="No contracts yet"
                  text="Upload your first contract to start organizing extracted information."
                  action={
                    <Link to="/contracts/upload">
                      <Button variant="primary">Upload Contract</Button>
                    </Link>
                  }
                />
              ) : !rows.length ? (
                <EmptyState icon="filter" title="No contracts found" text="No contracts match the current filters." />
              ) : (
                <>
                  <Card className="hidden overflow-x-auto md:block">
                    <table className="w-full min-w-[900px] text-left text-body">
                      <thead className="bg-canvas text-slate">
                        <tr>
                          {["Contract", "Parties", "Effective Date", "Expiry", "Status", "Last Updated", ""].map(
                            (h) => (
                              <th key={h} className="px-4 py-3 font-medium">
                                {h}
                              </th>
                            ),
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((c) => {
                          const s = contractStatus(c);
                          return (
                            <tr
                              key={c.id}
                              onClick={() => navigate(`/contracts/${c.id}`)}
                              className="group cursor-pointer border-t border-line hover:bg-indigo-soft/50"
                            >
                              <td className="px-4 py-4">
                                <Link className="flex items-center gap-3" to={`/contracts/${c.id}`}>
                                  <FileText className="h-5 w-5 text-slate" />
                                  <span>
                                    <b>{c.name}</b>
                                    <small className="block text-slate">
                                      {c.latest_version ? `Version ${c.latest_version.version_number}` : "No version"}
                                    </small>
                                  </span>
                                </Link>
                              </td>
                              <td className="px-4 py-4">{c.parties.join(" · ") || "—"}</td>
                              <td className="px-4 py-4">{fmtDate(c.effective_date)}</td>
                              <td className="px-4 py-4">{fmtDate(c.current_term_end)}</td>
                              <td className="px-4 py-4">
                                <StatusBadge kind={s.kind} label={s.label} />
                              </td>
                              <td className="px-4 py-4">{fmtDate(c.updated_at)}</td>
                              <td className="px-4 py-4">
                                <ChevronRight className="h-4 w-4 text-indigo opacity-0 group-hover:opacity-100" />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </Card>
                  <div className="grid gap-4 md:hidden">
                    {rows.map((c) => {
                      const s = contractStatus(c);
                      return (
                        <Link key={c.id} to={`/contracts/${c.id}`}>
                          <Card className="p-5">
                            <div className="flex justify-between gap-2 font-medium">
                              {c.name}
                              <StatusBadge kind={s.kind} label={s.label} />
                            </div>
                            <p className="mt-2 text-body text-slate">{c.parties.join(" · ")}</p>
                            <p className="mt-3 text-table text-slate">
                              Effective {fmtDate(c.effective_date)} · Expires {fmtDate(c.current_term_end)}
                            </p>
                            <p className="mt-2 text-table text-slate">Updated {fmtDate(c.updated_at)}</p>
                          </Card>
                        </Link>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          );
        }}
      </Async>
    </>
  );
}
