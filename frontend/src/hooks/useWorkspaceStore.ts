import { create } from "zustand";

type LeftTab = "discussion" | "preview";

interface WorkspaceUi {
  leftOpen: boolean;
  leftTab: LeftTab;
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  editingNodeId: string | null;
  expanded: Record<string, boolean>;
  toggleLeft: () => void;
  setLeftTab: (tab: LeftTab) => void;
  hover: (id: string | null) => void;
  select: (id: string | null) => void;
  edit: (id: string | null) => void;
  toggleExpanded: (id: string) => void;
  setAllExpanded: (ids: string[], open: boolean) => void;
  reset: () => void;
}

export const useWorkspaceStore = create<WorkspaceUi>((set) => ({
  leftOpen: false,
  leftTab: "discussion",
  hoveredNodeId: null,
  selectedNodeId: null,
  editingNodeId: null,
  expanded: {},
  toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
  setLeftTab: (leftTab) => set({ leftTab }),
  hover: (hoveredNodeId) => set({ hoveredNodeId }),
  select: (selectedNodeId) => set({ selectedNodeId, editingNodeId: null }),
  edit: (editingNodeId) => set((s) => ({ editingNodeId, selectedNodeId: editingNodeId ?? s.selectedNodeId })),
  toggleExpanded: (id) => set((s) => ({ expanded: { ...s.expanded, [id]: !s.expanded[id] } })),
  setAllExpanded: (ids, open) => set({ expanded: Object.fromEntries(ids.map((id) => [id, open])) }),
  reset: () => set({ leftOpen: false, leftTab: "discussion", hoveredNodeId: null, selectedNodeId: null, editingNodeId: null, expanded: {} }),
}));
