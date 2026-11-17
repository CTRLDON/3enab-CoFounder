import { describe, expect, it } from "vitest";
import { PLAN } from "../../test/fixtures";
import { layoutPlan, SIZE } from "./layout";

describe("layoutPlan", () => {
  it("places the venture in the centre and categories on both sides", () => {
    const { nodes, edges } = layoutPlan(PLAN.document.nodes, {}, PLAN.node_status);
    const centre = nodes.find((n) => n.id === "venture")!;
    expect(centre.data.kind).toBe("center");
    expect(nodes.find((n) => n.id === "strategy")!.position.x).toBeGreaterThan(0);
    expect(nodes.find((n) => n.id === "revenue")!.position.x).toBeLessThan(0);
    expect(edges).toHaveLength(4);
  });

  it("reveals children only when their branch is expanded", () => {
    expect(layoutPlan(PLAN.document.nodes, {}, {}).nodes.find((n) => n.id === "revenue-stream-1")).toBeUndefined();
    const open = layoutPlan(PLAN.document.nodes, { revenue: true }, {});
    expect(open.nodes.find((n) => n.id === "revenue-stream-1")).toBeDefined();
    expect(open.edges.some((e) => e.source === "revenue" && e.target === "revenue-stream-1")).toBe(true);
  });

  it("is stable and keeps nodes on the same side from overlapping", () => {
    const a = layoutPlan(PLAN.document.nodes, { revenue: true, costs: true }, {});
    const b = layoutPlan(PLAN.document.nodes, { revenue: true, costs: true }, {});
    expect(a.nodes.map((n) => n.position)).toEqual(b.nodes.map((n) => n.position));
    const left = a.nodes.filter((n) => n.data.kind === "main" && n.position.x < 0).sort((x, y) => x.position.y - y.position.y);
    for (let i = 1; i < left.length; i++) {
      expect(left[i].position.y).toBeGreaterThanOrEqual(left[i - 1].position.y + SIZE.main.h);
    }
  });
});
