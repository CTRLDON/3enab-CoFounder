import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VentureContext } from "../app/ventureContext";
import { useWorkspaceStore } from "../hooks/useWorkspaceStore";
import { PLAN, VENTURE } from "../test/fixtures";
import { Workspace } from "./Workspace";

vi.mock("../services/api", () => ({
  ApiError: class extends Error {},
  api: {
    plan: vi.fn(async () => PLAN),
    venture: vi.fn(async () => VENTURE),
    conversation: vi.fn(async () => ({ messages: [{ id: 1, role: "agent", agent: "skeptical_cofounder", content: "Who pays for this?", structured: { stance: "CHALLENGE" }, created_at: "" }] })),
    node: vi.fn(async (_v: string, id: string) => ({ node: PLAN.document.nodes.find((n) => n.id === id), evidence: [], history: [] })),
    demoScenarios: vi.fn(async () => ({ scenarios: {} })),
    negotiation: vi.fn(),
  },
}));

// React Flow keeps nodes visibility:hidden until it measures them, which jsdom cannot do,
// so nodes are located by their aria-label attribute rather than by accessible role/name.
function renderWorkspace() {
  return render(
    <MemoryRouter>
      <VentureContext.Provider value={{ venture: VENTURE, setVenture: vi.fn(), reload: vi.fn(async () => VENTURE), theme: null }}>
        <Workspace />
      </VentureContext.Provider>
    </MemoryRouter>,
  );
}

describe("Workspace", () => {
  beforeEach(() => useWorkspaceStore.getState().reset());

  it("renders the mind map from the stored plan", async () => {
    renderWorkspace();
    expect(await screen.findByText("Revenue model")).toBeInTheDocument();
    expect(screen.getByText("Business strategy")).toBeInTheDocument();
    expect(screen.getByText("Plan v1")).toBeInTheDocument();
    expect(screen.getByText("Economic role")).toBeInTheDocument();
  });

  it("expands and collapses the founder discussion panel", async () => {
    renderWorkspace();
    fireEvent.click(await screen.findByRole("button", { name: /Founder discussion/ }));
    expect(await screen.findByText("Who pays for this?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collapse the discussion panel" }));
    await waitFor(() => expect(screen.queryByText("Who pays for this?")).not.toBeInTheDocument());
  });

  it("opens the detail panel when a node is selected with the keyboard", async () => {
    renderWorkspace();
    const node = await waitFor(() => { const el = document.querySelector<HTMLElement>('[role="button"][aria-label^="Revenue model."]'); if (!el) throw new Error("node not rendered"); return el; });
    fireEvent.keyDown(node, { key: "Enter" });
    const panel = await screen.findByRole("complementary", { name: "Node details" });
    expect(within(panel).getByRole("heading", { name: "Revenue model" })).toBeInTheDocument();
    expect(within(panel).getByRole("tab", { name: "Economics" })).toBeInTheDocument();
  });

  it("shows a preview on focus and opens the edit negotiation from the pencil", async () => {
    renderWorkspace();
    const node = await waitFor(() => { const el = document.querySelector<HTMLElement>('[role="button"][aria-label^="Revenue model."]'); if (!el) throw new Error("node not rendered"); return el; });
    fireEvent.focus(node);
    expect(await screen.findByText("Main assumption text")).toBeInTheDocument();
    fireEvent.click(document.querySelector<HTMLElement>('button[aria-label="Propose a change to Revenue model"]')!);
    expect(await screen.findByText(/Nothing changes until you approve a revision/)).toBeInTheDocument();
  });
});
