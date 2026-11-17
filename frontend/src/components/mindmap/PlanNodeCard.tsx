import { Handle, Position, type NodeProps } from "@xyflow/react";
import { ChevronLeft, ChevronRight, Pencil } from "lucide-react";
import type { KeyboardEvent } from "react";
import { useWorkspaceStore } from "../../hooks/useWorkspaceStore";
import { ECONOMIC_META } from "../ui/Badges";
import { SIZE, type PlanFlowNode } from "./layout";

const PROGRESS_TEXT = { active: "In progress", complete: "Done", upcoming: "Later phase", stopped: "Stopped" } as const;

export function PlanNodeCard({ id, data, selected }: NodeProps<PlanFlowNode>) {
  const { node, kind, side, childCount, expanded, status } = data;
  const hover = useWorkspaceStore((s) => s.hover);
  const select = useWorkspaceStore((s) => s.select);
  const edit = useWorkspaceStore((s) => s.edit);
  const toggle = useWorkspaceStore((s) => s.toggleExpanded);
  const hovered = useWorkspaceStore((s) => s.hoveredNodeId === id);
  const econ = ECONOMIC_META[node.economic_class] ?? ECONOMIC_META.unknown;
  const size = SIZE[kind];
  const evidenceCount = Object.values(status?.evidence ?? {}).reduce((a, b) => a + (b ?? 0), 0);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(id); }
    if (e.key.toLowerCase() === "e" && kind !== "center") { e.preventDefault(); edit(id); }
    if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && kind === "main" && childCount) { e.preventDefault(); toggle(id); }
  };

  const ring = selected ? "ring-2 ring-[var(--c-accent)]" : hovered ? "ring-1 ring-[var(--c-control-border)]" : "";
  const Chevron = (side === "right") === expanded ? ChevronLeft : ChevronRight;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${node.title}. ${econ.label}. ${status ? PROGRESS_TEXT[status.progress] : ""}. Press Enter for details${kind !== "center" ? ", E to propose a change" : ""}.`}
      aria-pressed={selected}
      onFocus={() => hover(id)}
      onBlur={() => hover(null)}
      onKeyDown={onKey}
      style={{ width: size.w, minHeight: size.h }}
      className={`group relative flex overflow-hidden rounded-lg border bg-surface text-left outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-[var(--c-focus)] ${ring} ${
        kind === "center" ? "border-control shadow-[0_10px_30px_-18px_rgba(0,0,0,.35)]" : "border-line"
      } ${node.economic_class === "unknown" ? "border-dashed" : ""}`}
    >
      <Handle type="target" id="in-left" position={Position.Left} />
      <Handle type="target" id="in-right" position={Position.Right} />
      <Handle type="source" id="out-left" position={Position.Left} />
      <Handle type="source" id="out-right" position={Position.Right} />
      <span className={`econ-stripe econ-${node.economic_class}`} aria-hidden />
      <div className={`min-w-0 flex-1 ${kind === "center" ? "px-4 py-3" : "px-3 py-2"}`}>
        <div className="flex items-start gap-1.5">
          <econ.Icon className="mt-[3px] size-3.5 shrink-0" style={{ color: `var(--c-econ-${node.economic_class}-text)` }} aria-hidden />
          <p className={`min-w-0 flex-1 leading-snug ${kind === "center" ? "text-[1.07rem] font-semibold" : kind === "main" ? "font-semibold t-small" : "t-small"} line-clamp-2`}>
            {node.title}
          </p>
        </div>
        {kind === "center" ? <p className="mt-1 t-micro text-muted line-clamp-2">{node.summary}</p> : null}
        {kind !== "center" ? (
          <p className="mt-0.5 t-micro text-muted">
            {status ? PROGRESS_TEXT[status.progress] : ""}
            {evidenceCount ? `, ${evidenceCount} evidence` : ""}
            {status?.revisions ? `, edited ${status.revisions}×` : ""}
          </p>
        ) : null}
      </div>
      {kind !== "center" ? (
        <button
          type="button"
          aria-label={`Propose a change to ${node.title}`}
          onClick={(e) => { e.stopPropagation(); edit(id); }}
          className="nodrag absolute right-1.5 top-1.5 grid size-7 place-items-center rounded-md bg-surface text-muted opacity-0 transition-opacity hover:bg-sunken hover:text-ink focus-visible:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          <Pencil className="size-3.5" aria-hidden />
        </button>
      ) : null}
      {kind === "main" && childCount > 0 ? (
        <button
          type="button"
          aria-label={`${expanded ? "Collapse" : "Expand"} ${node.title} (${childCount} items)`}
          aria-expanded={expanded}
          onClick={(e) => { e.stopPropagation(); toggle(id); }}
          className="nodrag absolute bottom-1.5 right-1.5 inline-flex h-6 items-center gap-0.5 rounded-md px-1.5 t-micro text-muted hover:bg-sunken hover:text-ink"
        >
          {childCount}
          <Chevron className="size-3.5" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
