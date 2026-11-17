import { Background, BackgroundVariant, Controls, ReactFlow, useReactFlow, type Edge } from "@xyflow/react";
import { useEffect, useMemo } from "react";
import { useWorkspaceStore } from "../../hooks/useWorkspaceStore";
import type { Plan } from "../../types/api";
import { layoutPlan } from "./layout";
import { PlanNodeCard } from "./PlanNodeCard";

const nodeTypes = { plan: PlanNodeCard };
const reducedMotion = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function MindMap({ plan, layoutKey }: { plan: Plan; layoutKey: string }) {
  const expanded = useWorkspaceStore((s) => s.expanded);
  const hovered = useWorkspaceStore((s) => s.hoveredNodeId);
  const selected = useWorkspaceStore((s) => s.selectedNodeId);
  const hover = useWorkspaceStore((s) => s.hover);
  const select = useWorkspaceStore((s) => s.select);
  const flow = useReactFlow();

  const graph = useMemo(() => layoutPlan(plan.document.nodes, expanded, plan.node_status), [plan, expanded]);
  const nodes = useMemo(() => graph.nodes.map((n) => ({ ...n, selected: n.id === selected })), [graph, selected]);
  const edges: Edge[] = useMemo(() => {
    const focus = hovered ?? selected;
    return graph.edges.map((e) => ({ ...e, className: focus && (e.source === focus || e.target === focus) ? "is-related" : undefined }));
  }, [graph, hovered, selected]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const duration = reducedMotion() ? 0 : 320;
      const focus = useWorkspaceStore.getState().selectedNodeId;
      if (focus) {
        // Keep the selected node and its neighbours readable instead of shrinking the whole map.
        const related = graph.nodes.filter((n) => n.id === focus || n.data.node.parent_id === focus || n.id === graph.nodes.find((x) => x.id === focus)?.data.node.parent_id);
        void flow.fitView({ nodes: related.map((n) => ({ id: n.id })), padding: 0.3, maxZoom: 0.95, minZoom: 0.7, duration });
      } else {
        void flow.fitView({ padding: 0.16, maxZoom: 0.95, minZoom: 0.4, duration });
      }
    }, 280);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutKey, flow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      nodesDraggable={false}
      nodesConnectable={false}
      nodesFocusable={false}
      edgesFocusable={false}
      fitView
      fitViewOptions={{ padding: 0.16, maxZoom: 0.95 }}
      minZoom={0.25}
      maxZoom={1.6}
      onNodeMouseEnter={(_, node) => hover(node.id)}
      onNodeMouseLeave={() => hover(null)}
      onNodeClick={(_, node) => select(node.id)}
      onPaneClick={() => select(null)}
      proOptions={{ hideAttribution: false }}
      aria-label="Business mind map"
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--c-border)" />
      <Controls showInteractive={false} position="bottom-right" />
    </ReactFlow>
  );
}
