import type { Edge, Node } from "@xyflow/react";
import type { NodeStatus, PlanNode } from "../../types/api";

export type NodeKind = "center" | "main" | "child";
export type Side = "left" | "right";

export interface PlanNodeData extends Record<string, unknown> {
  node: PlanNode;
  kind: NodeKind;
  side: Side;
  childCount: number;
  expanded: boolean;
  status?: NodeStatus;
}

export type PlanFlowNode = Node<PlanNodeData, "plan">;

// Discover/validate topics read on the right; build/sell/operate topics on the left.
export const RIGHT_ORDER = ["strategy", "market", "problems", "competitors", "value", "risks"];
export const LEFT_ORDER = ["product", "revenue", "costs", "marketing", "launch", "operations"];

export const SIZE = { center: { w: 280, h: 96 }, main: { w: 232, h: 58 }, child: { w: 216, h: 50 } } as const;
const MAIN_X = 340;
const CHILD_X = 640;
const CHILD_ROW = 62;
const BLOCK_GAP = 22;

export function layoutPlan(
  nodes: PlanNode[],
  expanded: Record<string, boolean>,
  status: Record<string, NodeStatus>,
): { nodes: PlanFlowNode[]; edges: Edge[] } {
  const center = nodes.find((n) => n.parent_id === null) ?? nodes[0];
  const mains = nodes.filter((n) => n.parent_id === center.id);
  const childrenOf = (id: string) => nodes.filter((n) => n.parent_id === id);

  const right = RIGHT_ORDER.map((id) => mains.find((m) => m.id === id)).filter(Boolean) as PlanNode[];
  const left = LEFT_ORDER.map((id) => mains.find((m) => m.id === id)).filter(Boolean) as PlanNode[];
  for (const m of mains) {
    if (!right.includes(m) && !left.includes(m)) (right.length <= left.length ? right : left).push(m);
  }

  const flowNodes: PlanFlowNode[] = [
    {
      id: center.id, type: "plan", position: { x: -SIZE.center.w / 2, y: -SIZE.center.h / 2 },
      data: { node: center, kind: "center", side: "right", childCount: mains.length, expanded: true, status: status[center.id] },
    },
  ];
  const edges: Edge[] = [];

  const placeSide = (list: PlanNode[], side: Side) => {
    const blocks = list.map((m) => {
      const kids = childrenOf(m.id);
      const open = Boolean(expanded[m.id]) && kids.length > 0;
      const height = Math.max(SIZE.main.h, open ? kids.length * CHILD_ROW - (CHILD_ROW - SIZE.child.h) : 0);
      return { m, kids, open, height };
    });
    const total = blocks.reduce((sum, b) => sum + b.height, 0) + BLOCK_GAP * Math.max(0, blocks.length - 1);
    let top = -total / 2;
    for (const { m, kids, open, height } of blocks) {
      const mainY = top + height / 2 - SIZE.main.h / 2;
      const mainX = side === "right" ? MAIN_X - SIZE.main.w / 2 + 20 : -MAIN_X - SIZE.main.w / 2 - 20;
      flowNodes.push({
        id: m.id, type: "plan", position: { x: mainX, y: mainY },
        data: { node: m, kind: "main", side, childCount: kids.length, expanded: open, status: status[m.id] },
      });
      edges.push({
        id: `${center.id}-${m.id}`, source: center.id, target: m.id,
        sourceHandle: side === "right" ? "out-right" : "out-left", targetHandle: side === "right" ? "in-left" : "in-right",
      });
      if (open) {
        kids.forEach((kid, index) => {
          const y = top + (height - (kids.length * CHILD_ROW - (CHILD_ROW - SIZE.child.h))) / 2 + index * CHILD_ROW;
          const x = side === "right" ? CHILD_X - SIZE.child.w / 2 + 40 : -CHILD_X - SIZE.child.w / 2 - 40;
          flowNodes.push({
            id: kid.id, type: "plan", position: { x, y },
            data: { node: kid, kind: "child", side, childCount: 0, expanded: false, status: status[kid.id] },
          });
          edges.push({
            id: `${m.id}-${kid.id}`, source: m.id, target: kid.id,
            sourceHandle: side === "right" ? "out-right" : "out-left", targetHandle: side === "right" ? "in-left" : "in-right",
          });
        });
      }
      top += height + BLOCK_GAP;
    }
  };
  placeSide(right, "right");
  placeSide(left, "left");
  return { nodes: flowNodes, edges };
}
