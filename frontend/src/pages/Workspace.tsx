import { ReactFlowProvider } from "@xyflow/react";
import { ListTree, MessageSquare } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { useVenture } from "../app/ventureContext";
import { LeftPanel } from "../components/business/LeftPanel";
import { NegotiationPanel } from "../components/business/NegotiationPanel";
import { NodeDetailPanel } from "../components/business/NodeDetailPanel";
import { NodePreview } from "../components/business/NodePreview";
import { Legend } from "../components/mindmap/Legend";
import { MindMap } from "../components/mindmap/MindMap";
import { OutcomeBadge } from "../components/ui/Badges";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorNotice, Loading } from "../components/ui/Feedback";
import { useResource } from "../hooks/useResource";
import { useWorkspaceStore } from "../hooks/useWorkspaceStore";
import { api } from "../services/api";
import type { Plan } from "../types/api";

const PHASES = ["Discover", "Validate", "Build", "Commercial", "Launch", "Operate"];

function PhaseStrip() {
  const { venture } = useVenture();
  return (
    <Link to={`/v/${venture.id}/phases`} aria-label="Open phase progress"
      className="flex items-center gap-1 rounded-lg border border-line bg-surface/95 p-1.5 backdrop-blur hover:border-control">
      {PHASES.map((name, i) => {
        const phase = i + 1;
        const gate = venture.gates[String(phase)];
        const current = venture.current_phase === phase && venture.state !== "STOPPED";
        return (
          <span key={name} className={`flex items-center gap-1 rounded-md px-2 py-1 t-micro ${current ? "bg-accent-soft text-accent-text font-semibold" : "text-muted"}`}>
            {phase}. {name}
            {gate ? <OutcomeBadge outcome={gate.outcome} /> : null}
          </span>
        );
      })}
    </Link>
  );
}

export function Workspace() {
  const { venture, setVenture } = useVenture();
  const location = useLocation();
  const planRes = useResource(() => api.plan(venture.id), [venture.id]);
  const ui = useWorkspaceStore();
  const [notice, setNotice] = useState<string | null>(
    (location.state as { fromApproval?: boolean } | null)?.fromApproval ? "Plan v1 created from your approved proposal." : null,
  );

  useEffect(() => () => ui.reset(), []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(t);
  }, [notice]);

  if (planRes.loading && !planRes.data) return <div className="p-8"><Loading label="Loading the business map" /></div>;
  if (planRes.error || !planRes.data) {
    return (
      <div className="mx-auto max-w-xl p-8 space-y-4">
        <ErrorNotice error={planRes.error} onRetry={planRes.reload} />
        <EmptyState title="No business map yet">Approve a proposal in the discussion to create one.</EmptyState>
      </div>
    );
  }
  const plan = planRes.data;
  const nodes = plan.document.nodes;
  const selectedNode = nodes.find((n) => n.id === ui.selectedNodeId) ?? null;
  const editingNode = nodes.find((n) => n.id === ui.editingNodeId) ?? null;
  const hoveredNode = nodes.find((n) => n.id === ui.hoveredNodeId) ?? null;
  const rightOpen = Boolean(selectedNode || editingNode);
  const mainIds = nodes.filter((n) => nodes.some((c) => c.parent_id === n.id) && n.parent_id).map((n) => n.id);
  const allOpen = mainIds.length > 0 && mainIds.every((id) => ui.expanded[id]);
  const layoutKey = `${ui.leftOpen}-${rightOpen}-${ui.selectedNodeId}-${plan.current_version}`;

  const onPlanChanged = async (next: Plan) => {
    planRes.setData(next);
    const v = await api.venture(venture.id);
    setVenture(v);
    if (next.current_version !== plan.current_version) setNotice(`Plan updated to v${next.current_version}.`);
  };

  return (
    <div
      className="grid h-[calc(100vh-97px)] min-h-[520px] transition-[grid-template-columns] duration-300"
      style={{ gridTemplateColumns: `${ui.leftOpen ? "minmax(280px, 360px)" : "0px"} minmax(0,1fr) ${rightOpen ? "minmax(320px, 420px)" : "0px"}` }}
    >
      <aside aria-label="Founder discussion and node preview" className={`min-w-0 overflow-hidden border-line bg-surface ${ui.leftOpen ? "border-r" : ""}`}>
        {ui.leftOpen ? <div className="h-full panel-enter" style={{ ["--panel-from" as string]: "-12px" }}><LeftPanel plan={plan} /></div> : null}
      </aside>

      <section aria-label="Business map" className="relative min-w-0">
        <ReactFlowProvider>
          <MindMap plan={plan} layoutKey={layoutKey} />
        </ReactFlowProvider>

        <div className="pointer-events-none absolute inset-x-3 top-3 flex items-start justify-between gap-3">
          <div className="pointer-events-auto space-y-2">
            {!ui.leftOpen ? (
              <button type="button" onClick={ui.toggleLeft} aria-expanded={false}
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-line bg-surface px-3 t-small font-medium hover:border-control">
                <MessageSquare className="size-4" aria-hidden /> Founder discussion
              </button>
            ) : null}
            {!ui.leftOpen && hoveredNode ? (
              <div className="w-72 rounded-lg border border-line bg-surface p-3.5 shadow-[0_10px_30px_-20px_rgba(0,0,0,.4)]" aria-live="polite">
                <NodePreview node={hoveredNode} status={plan.node_status[hoveredNode.id]} />
              </div>
            ) : null}
          </div>
          {!ui.leftOpen && !rightOpen ? <div className="pointer-events-auto hidden xl:block"><PhaseStrip /></div> : null}
          <div className="pointer-events-auto flex gap-2">
            <Button size="sm" className="whitespace-nowrap" icon={<ListTree className="size-4" aria-hidden />} onClick={() => ui.setAllExpanded(mainIds, !allOpen)}>
              {allOpen ? "Collapse all" : "Expand all"}
            </Button>
            <span className="inline-flex h-8 items-center whitespace-nowrap rounded-md border border-line bg-surface px-2.5 t-micro text-muted" title={plan.reason}>
              Plan v{plan.current_version}
            </span>
          </div>
        </div>

        <div className="absolute bottom-3 left-3"><Legend key={String(ui.leftOpen || rightOpen)} defaultOpen={!ui.leftOpen && !rightOpen} /></div>
        {notice ? (
          <div role="status" className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-lg bg-ink px-4 py-2 t-small text-bg fade-in">
            {notice}
          </div>
        ) : null}
        {nodes.length <= 1 ? <div className="absolute inset-0 grid place-items-center"><EmptyState title="This plan has no sections yet." /></div> : null}
      </section>

      <aside aria-label="Node details" className={`min-w-0 overflow-hidden border-line bg-surface ${rightOpen ? "border-l" : ""}`}>
        {editingNode ? (
          <div className="h-full panel-enter" key={`edit-${editingNode.id}`}>
            <NegotiationPanel node={editingNode} plan={plan} onPlanChanged={onPlanChanged} onClose={() => ui.select(editingNode.id)} />
          </div>
        ) : selectedNode ? (
          <div className="h-full panel-enter" key={selectedNode.id}><NodeDetailPanel node={selectedNode} plan={plan} /></div>
        ) : null}
      </aside>
    </div>
  );
}
