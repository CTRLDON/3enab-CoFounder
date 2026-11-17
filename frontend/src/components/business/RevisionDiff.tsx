import type { PlanNode, ProposedRevision } from "../../types/api";

const List = ({ items }: { items: string[] }) => <ul className="list-disc space-y-1 pl-4">{items.map((i) => <li key={i}>{i}</li>)}</ul>;

export function RevisionDiff({ revision, nodes }: { revision: ProposedRevision; nodes: PlanNode[] }) {
  const title = (id: string) => nodes.find((n) => n.id === id)?.title ?? id;
  return (
    <div className="space-y-4 t-small">
      <div className="grid gap-2">
        <div className="rounded-md bg-sunken p-3">
          <p className="t-micro font-semibold text-muted">Current plan</p>
          <p className="mt-1">{revision.current_plan}</p>
        </div>
        <div className="rounded-md border border-accent bg-accent-soft p-3">
          <p className="t-micro font-semibold text-accent-text">Proposed plan</p>
          <p className="mt-1">{revision.proposed_plan}</p>
        </div>
      </div>
      <div><p className="font-semibold">Reasons for the change</p><List items={revision.reasons} /></div>
      <div><p className="font-semibold">Potential consequences</p><List items={revision.consequences} /></div>
      <div><p className="font-semibold">Affected nodes</p><p>{revision.affected_nodes.map(title).join(", ")}</p></div>
      <div><p className="font-semibold">Remaining risks</p><List items={revision.remaining_risks} /></div>
      <details>
        <summary className="cursor-pointer text-muted">Exact field changes ({revision.changes.length})</summary>
        <ul className="mt-2 space-y-1.5">
          {revision.changes.map((c, i) => (
            <li key={i}><span className="font-medium">{title(c.node_id)}</span> <span className="text-muted">{c.field.replace(/_/g, " ")}:</span>{" "}
              {Array.isArray(c.value) ? c.value.join("; ") : c.value}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
