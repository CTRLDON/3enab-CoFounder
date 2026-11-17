import { useState } from "react";
import { useVenture } from "../app/ventureContext";
import { EvidenceTable } from "../components/research/EvidenceTable";
import { EvidenceBadge } from "../components/ui/Badges";
import { EmptyState, ErrorNotice, Skeleton } from "../components/ui/Feedback";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { EvidenceClass } from "../types/api";

const CLASSES: EvidenceClass[] = ["VERIFIED", "ESTIMATE", "ASSUMPTION", "PROJECTION", "MOCKED", "UNKNOWN"];

export function Evidence() {
  const { venture } = useVenture();
  const data = useResource(() => api.evidence(venture.id), [venture.id]);
  const [filter, setFilter] = useState<EvidenceClass | "all">("all");
  const records = (data.data ?? []).filter((r) => filter === "all" || r.classification === filter);
  const counts = Object.fromEntries(CLASSES.map((c) => [c, (data.data ?? []).filter((r) => r.classification === c).length]));
  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="t-title">Evidence register</h1>
      <p className="mt-2 measure text-muted">
        Why Mate recommends what it does. Only sources Mate retrieved itself can be VERIFIED or ESTIMATE; everything else stays an
        assumption until real evidence arrives. The model's confidence is never counted as evidence.
      </p>
      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Filter by evidence class">
        <button type="button" onClick={() => setFilter("all")} aria-pressed={filter === "all"}
          className={`rounded-md border px-2.5 py-1 t-small ${filter === "all" ? "border-accent bg-accent-soft" : "border-line"}`}>All {data.data?.length ?? 0}</button>
        {CLASSES.map((c) => (
          <button key={c} type="button" onClick={() => setFilter(c)} aria-pressed={filter === c}
            className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 ${filter === c ? "border-accent" : "border-line"}`}>
            <EvidenceBadge value={c} /><span className="t-micro">{counts[c]}</span>
          </button>
        ))}
      </div>
      <div className="mt-6">
        {data.loading ? <Skeleton lines={5} /> : null}
        <ErrorNotice error={data.error} onRetry={data.reload} />
        {data.data && !records.length ? <EmptyState title="No evidence here yet">Run Phase 1 research, or add evidence with a source.</EmptyState> : null}
        {records.length ? <EvidenceTable records={records} /> : null}
      </div>
    </div>
  );
}
