import { MessageSquareText, X } from "lucide-react";
import { Link } from "react-router";
import { useVenture } from "../../app/ventureContext";
import { useResource } from "../../hooks/useResource";
import { useWorkspaceStore } from "../../hooks/useWorkspaceStore";
import { api } from "../../services/api";
import type { Plan } from "../../types/api";
import { MessageList } from "../chat/MessageList";
import { Skeleton } from "../ui/Feedback";
import { Tabs } from "../ui/Tabs";
import { NodePreview } from "./NodePreview";

export function LeftPanel({ plan }: { plan: Plan }) {
  const { venture } = useVenture();
  const tab = useWorkspaceStore((s) => s.leftTab);
  const setTab = useWorkspaceStore((s) => s.setLeftTab);
  const toggle = useWorkspaceStore((s) => s.toggleLeft);
  const hovered = useWorkspaceStore((s) => s.hoveredNodeId);
  const selected = useWorkspaceStore((s) => s.selectedNodeId);
  const convo = useResource(() => api.conversation(venture.id), [venture.id]);
  const previewId = hovered ?? selected;
  const previewNode = plan.document.nodes.find((n) => n.id === previewId);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 px-4 pt-3">
        <p className="inline-flex items-center gap-2 t-small font-semibold"><MessageSquareText className="size-4" aria-hidden />Founder discussion</p>
        <button type="button" onClick={toggle} aria-label="Collapse the discussion panel" className="grid size-8 place-items-center rounded-md text-muted hover:bg-sunken hover:text-ink">
          <X className="size-4" aria-hidden />
        </button>
      </div>
      <div className="px-4 pt-2">
        <Tabs label="Left panel" value={tab} onChange={(v) => setTab(v as "discussion" | "preview")}
          items={[{ id: "discussion", label: "Discussion" }, { id: "preview", label: <>Node preview{previewNode && tab !== "preview" ? <span className="ml-1.5 inline-block size-1.5 rounded-full bg-accent align-middle" aria-label="(new)" /> : null}</> }]} />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {tab === "discussion" ? (
          <>
            {convo.loading ? <Skeleton lines={5} /> : <MessageList messages={convo.data?.messages ?? []} ventureId={venture.id} compact />}
            <Link to={`/v/${venture.id}/discuss`} className="mt-6 inline-block t-small text-accent-text underline underline-offset-2">Open the full discussion</Link>
          </>
        ) : previewNode ? (
          <NodePreview node={previewNode} status={plan.node_status[previewNode.id]} />
        ) : (
          <p className="t-small text-muted">Hover over or focus a node on the map to preview it here.</p>
        )}
      </div>
    </div>
  );
}
