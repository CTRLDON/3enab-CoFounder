import { NavLink, Link } from "react-router";
import { STATE_LABEL, hasWorkspace } from "../../app/stateLabels";
import type { Theme, Venture } from "../../types/api";
import { MockedLabel } from "../ui/Badges";
import { PaletteChip } from "./PaletteChip";

export function TopBar({ venture, theme }: { venture: Venture; theme: Theme | null }) {
  const workspace = hasWorkspace(venture.state, venture.plan_version);
  const tabs = [
    { to: "discuss", label: "Discussion", enabled: true },
    { to: "map", label: "Business map", enabled: workspace || venture.plan_version !== null },
    { to: "phases", label: "Phases", enabled: venture.plan_version !== null },
    { to: "evidence", label: "Evidence", enabled: venture.plan_version !== null },
    { to: "artifacts", label: "Artifacts", enabled: true },
    { to: "audit", label: "Decision log", enabled: true },
  ];
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
      <div className="flex h-14 items-center gap-4 px-4">
        <Link to="/" className="font-semibold tracking-tight text-[1.07rem]" aria-label="Mate home">Mate</Link>
        <span className="h-5 w-px bg-line" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium leading-tight">{venture.title}</p>
          <p className="t-micro text-muted leading-tight">
            {STATE_LABEL[venture.state]}{venture.plan_version ? `, plan v${venture.plan_version}` : ""}
          </p>
        </div>
        {venture.mode === "demo" ? <MockedLabel text="Scripted demo" /> : null}
        <PaletteChip theme={theme} />
      </div>
      <nav aria-label="Venture sections" className="flex gap-1 overflow-x-auto px-3">
        {tabs.map((tab) =>
          tab.enabled ? (
            <NavLink key={tab.to} to={tab.to}
              className={({ isActive }) => `-mb-px whitespace-nowrap border-b-2 px-2.5 py-2 t-small font-medium ${isActive ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`}>
              {tab.label}
            </NavLink>
          ) : (
            <span key={tab.to} className="whitespace-nowrap px-2.5 py-2 t-small text-muted/60" title="Available after you approve a proposal">{tab.label}</span>
          ),
        )}
      </nav>
    </header>
  );
}
