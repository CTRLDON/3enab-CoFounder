import { Pencil } from "lucide-react";
import { useWorkspaceStore } from "../../hooks/useWorkspaceStore";
import type { EvidenceClass, NodeStatus, PlanNode } from "../../types/api";
import { EconomicBadge, EvidenceBadge } from "../ui/Badges";

const PROGRESS = { active: "In progress now", complete: "Done", upcoming: "Comes in a later phase", stopped: "Venture stopped" } as const;

export function NodePreview({ node, status }: { node: PlanNode; status?: NodeStatus }) {
  const edit = useWorkspaceStore((s) => s.edit);
  const evidence = Object.entries(status?.evidence ?? {}) as [EvidenceClass, number][];
  return (
    <div className="space-y-3 fade-in">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold leading-snug">{node.title}</h3>
        {node.parent_id ? (
          <button type="button" onClick={() => edit(node.id)} aria-label={`Propose a change to ${node.title}`}
            className="grid size-7 shrink-0 place-items-center rounded-md text-muted hover:bg-sunken hover:text-ink">
            <Pencil className="size-3.5" aria-hidden />
          </button>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-1.5">
        <EconomicBadge value={node.economic_class} />
        {status ? <span className="rounded bg-sunken px-1.5 py-0.5 t-micro">{PROGRESS[status.progress]}</span> : null}
      </div>
      {node.objective ? <p className="t-small"><span className="text-muted">Objective. </span>{node.objective}</p> : null}
      {node.summary && node.summary !== node.objective ? <p className="t-small line-clamp-4">{node.summary}</p> : null}
      {node.main_assumption ? (
        <div className="t-small"><p className="text-muted">Main assumption</p><p>{node.main_assumption}</p></div>
      ) : null}
      {node.evidence_gap ? (
        <div className="t-small"><p className="text-muted">Evidence gap</p><p>{node.evidence_gap}</p></div>
      ) : null}
      {evidence.length ? (
        <div className="flex flex-wrap gap-1.5">{evidence.map(([k, n]) => <span key={k} className="inline-flex items-center gap-1"><EvidenceBadge value={k} compact /><span className="t-micro">{n}</span></span>)}</div>
      ) : <p className="t-micro text-muted">No evidence linked yet.</p>}
    </div>
  );
}
