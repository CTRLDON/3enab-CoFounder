import { ExternalLink, Pencil, X } from "lucide-react";
import { useState } from "react";
import { useVenture } from "../../app/ventureContext";
import { useResource } from "../../hooks/useResource";
import { useWorkspaceStore } from "../../hooks/useWorkspaceStore";
import { api } from "../../services/api";
import type { MoneyEstimate, Plan, PlanNode } from "../../types/api";
import { EconomicBadge, EvidenceBadge } from "../ui/Badges";
import { Button } from "../ui/Button";
import { ErrorNotice, Skeleton } from "../ui/Feedback";
import { Tabs } from "../ui/Tabs";

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="space-y-1.5"><h3 className="t-small font-semibold text-muted">{title}</h3><div className="t-small">{children}</div></section>;
}
const Items = ({ items, empty }: { items: string[]; empty: string }) =>
  items.length ? <ul className="list-disc space-y-1 pl-4">{items.map((i) => <li key={i}>{i}</li>)}</ul> : <p className="text-muted">{empty}</p>;

function Money({ value, label }: { value: MoneyEstimate | null; label: string }) {
  if (!value) return <Block title={label}><p className="text-muted">Not estimated.</p></Block>;
  return (
    <Block title={label}>
      <p className="flex flex-wrap items-center gap-2">
        <span className="text-base font-semibold tabular-nums">{value.amount === null ? "Unknown" : `${value.amount.toLocaleString()} ${value.currency}`}</span>
        <span className="text-muted">{value.period}</span>
        <EvidenceBadge value={value.classification} />
      </p>
      {value.basis ? <p className="text-muted mt-1">{value.basis}</p> : null}
    </Block>
  );
}

const TABS = [
  { id: "overview", label: "Overview" }, { id: "economics", label: "Economics" }, { id: "evidence", label: "Evidence" },
  { id: "tasks", label: "Tasks" }, { id: "history", label: "History" },
];

export function NodeDetailPanel({ node, plan }: { node: PlanNode; plan: Plan }) {
  const { venture } = useVenture();
  const select = useWorkspaceStore((s) => s.select);
  const edit = useWorkspaceStore((s) => s.edit);
  const [tab, setTab] = useState("overview");
  const detail = useResource(() => api.node(venture.id, node.id), [venture.id, node.id, plan.current_version]);
  const status = plan.node_status[node.id];
  const dependencies = node.dependencies.length ? node.dependencies : node.parent_id ? [plan.document.nodes.find((n) => n.id === node.parent_id)?.title ?? ""] : [];

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-line px-5 pb-0 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <EconomicBadge value={node.economic_class} />
            <h2 className="t-section mt-2 leading-snug">{node.title}</h2>
          </div>
          <button type="button" onClick={() => select(null)} aria-label="Close details" className="grid size-8 place-items-center rounded-md text-muted hover:bg-sunken hover:text-ink">
            <X className="size-4" aria-hidden />
          </button>
        </div>
        {node.parent_id ? (
          <Button className="mt-3" size="sm" icon={<Pencil className="size-3.5" aria-hidden />} onClick={() => edit(node.id)}>Propose a change</Button>
        ) : null}
        <div className="mt-4"><Tabs label="Node details" items={TABS} value={tab} onChange={setTab} /></div>
      </div>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
        {tab === "overview" ? (
          <>
            <Block title="Purpose">{node.objective || <span className="text-muted">Not set.</span>}</Block>
            <Block title="Explanation">{node.explanation || node.summary || <span className="text-muted">Not set.</span>}</Block>
            <Block title="Recommended strategy">{node.strategy || <span className="text-muted">Not set yet.</span>}</Block>
            <Block title="Implementation requirements"><Items items={node.requirements} empty="Defined when this node's phase runs." /></Block>
            <Block title="Depends on"><Items items={dependencies.filter(Boolean)} empty="Nothing." /></Block>
          </>
        ) : null}
        {tab === "economics" ? (
          <>
            <Block title="Economic role"><EconomicBadge value={node.economic_class} /></Block>
            <Money value={node.estimated_expense} label="Estimated expense" />
            <Money value={node.revenue_contribution} label="Potential revenue contribution" />
            <p className="t-micro text-muted">Figures show their currency, period and evidence class. A revenue role means potential income, never guaranteed profit.</p>
          </>
        ) : null}
        {tab === "evidence" ? (
          <>
            <Block title="Main assumption">{node.main_assumption || <span className="text-muted">None recorded.</span>}</Block>
            <Block title="Evidence gap">{node.evidence_gap || <span className="text-muted">None recorded.</span>}</Block>
            <Block title="Assumptions"><Items items={node.assumptions} empty="None listed." /></Block>
            <Block title="Risks"><Items items={node.risks} empty="None listed." /></Block>
            <Block title="Research evidence">
              {detail.loading ? <Skeleton /> : null}
              <ErrorNotice error={detail.error} onRetry={detail.reload} />
              {detail.data?.evidence.length ? (
                <ul className="space-y-3">
                  {detail.data.evidence.map((e) => (
                    <li key={e.id} className="space-y-1">
                      <EvidenceBadge value={e.classification} />
                      <p>{e.claim}</p>
                      {e.source_url ? (
                        <a href={e.source_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-accent-text underline underline-offset-2">
                          {e.source_title ?? e.source_url}<ExternalLink className="size-3" aria-hidden />
                        </a>
                      ) : null}
                      {e.limitations ? <p className="t-micro text-muted">{e.limitations}</p> : null}
                    </li>
                  ))}
                </ul>
              ) : detail.data ? <p className="text-muted">No evidence linked to this node yet. Phase 1 research attaches what it can find.</p> : null}
            </Block>
          </>
        ) : null}
        {tab === "tasks" ? (
          <>
            <Block title="Current progress">{status ? { active: "In progress now", complete: "Done", upcoming: `Phase ${node.phase}, not started`, stopped: "Venture stopped" }[status.progress] : "Unknown"}</Block>
            <Block title="Validation tasks"><Items items={node.validation_tasks} empty="None yet." /></Block>
            <Block title="Next actions"><Items items={node.next_actions} empty="None yet." /></Block>
          </>
        ) : null}
        {tab === "history" ? (
          <Block title="Edit history">
            {detail.data?.history.length ? (
              <ol className="space-y-3">
                {detail.data.history.map((h, i) => (
                  <li key={i}><p className="font-medium">v{h.from_version} to v{h.to_version}, approved by {h.approved_by}</p><p className="text-muted">{h.summary}</p></li>
                ))}
              </ol>
            ) : <p className="text-muted">Unchanged since the plan was approved (v1).</p>}
          </Block>
        ) : null}
      </div>
    </div>
  );
}
