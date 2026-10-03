import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import ObligationTable from "@/components/obligations/ObligationTable";
import ObligationDetail from "@/components/obligations/ObligationDetail";
import { Async, TableSkeleton, EmptyState } from "@/components/ui/States";
export default function ObligationsTab({ contractId, versionId }) {
  const a = useApi(() => api.obligations({ contract_id: contractId, version_id: versionId }), [contractId, versionId]);
  const [id, setId] = useState("");
  return (
    <Async state={a} skeleton={<TableSkeleton />}>
      {(items) => {
        const selected = items.find((o) => o.id === id) ?? items[0];
        return items.length ? (
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,1fr)]">
            <ObligationTable items={items} selected={selected?.id} onSelect={(o) => setId(o.id)} />
            {selected && (
              <ObligationDetail
                item={selected}
                onReviewed={a.reload}
                onStatus={async (s) => {
                  await api.setObligationStatus(selected.id, s);
                  a.reload();
                }}
              />
            )}
          </div>
        ) : (
          <EmptyState title="No obligations found" text="No obligations were extracted from this contract version." />
        );
      }}
    </Async>
  );
}
