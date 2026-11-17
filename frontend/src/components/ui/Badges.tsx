import { ArrowDownRight, ArrowUpDown, ArrowUpRight, CircleCheck, CircleDashed, CircleHelp, Compass, FlaskConical, Sigma, TrendingUp } from "lucide-react";
import type { EconomicClass, EvidenceClass, GateOutcome } from "../../types/api";

const EVIDENCE_ICON = {
  VERIFIED: CircleCheck, ESTIMATE: Sigma, ASSUMPTION: CircleDashed, PROJECTION: TrendingUp, MOCKED: FlaskConical, UNKNOWN: CircleHelp,
} as const;
const EVIDENCE_HELP: Record<EvidenceClass, string> = {
  VERIFIED: "Supported by a source Mate retrieved",
  ESTIMATE: "A sourced third-party estimate",
  ASSUMPTION: "Not verified yet",
  PROJECTION: "A modelled scenario, not a fact",
  MOCKED: "Demo or test data, not real",
  UNKNOWN: "Cannot be established yet",
};

export function EvidenceBadge({ value, compact = false }: { value: EvidenceClass; compact?: boolean }) {
  const Icon = EVIDENCE_ICON[value] ?? CircleHelp;
  const key = value.toLowerCase();
  return (
    <span
      title={EVIDENCE_HELP[value]}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 t-micro font-semibold whitespace-nowrap"
      style={{ background: `var(--c-ev-${key}-bg)`, color: `var(--c-ev-${key}-fg)` }}
    >
      <Icon className="size-3.5" aria-hidden />
      {compact ? null : value}
      {compact ? <span className="sr-only">{value}</span> : null}
    </span>
  );
}

export const ECONOMIC_META: Record<EconomicClass, { label: string; Icon: typeof ArrowUpRight; hint: string }> = {
  revenue: { label: "Potential revenue", Icon: ArrowUpRight, hint: "Could bring money in — not a promise of profit" },
  expense: { label: "Expense", Icon: ArrowDownRight, hint: "Costs money or time" },
  mixed: { label: "Revenue and expense", Icon: ArrowUpDown, hint: "Both costs and could earn" },
  strategic: { label: "Strategic", Icon: Compass, hint: "Shapes decisions; no direct money flow" },
  unknown: { label: "Unknown impact", Icon: CircleHelp, hint: "Economic effect not established" },
};

export function EconomicBadge({ value }: { value: EconomicClass }) {
  const meta = ECONOMIC_META[value] ?? ECONOMIC_META.unknown;
  return (
    <span
      title={meta.hint}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 t-micro font-medium whitespace-nowrap"
      style={{ background: `var(--c-econ-${value}-soft)`, color: `var(--c-econ-${value}-text)` }}
    >
      <meta.Icon className="size-3.5" aria-hidden />
      {meta.label}
    </span>
  );
}

const OUTCOME_STYLE: Record<GateOutcome, { bg: string; fg: string; text: string }> = {
  GO: { bg: "var(--c-ev-verified-bg)", fg: "var(--c-ev-verified-fg)", text: "Go" },
  REPEAT: { bg: "var(--c-ev-assumption-bg)", fg: "var(--c-ev-assumption-fg)", text: "Repeat" },
  PIVOT: { bg: "var(--c-ev-projection-bg)", fg: "var(--c-ev-projection-fg)", text: "Pivot" },
  STOP: { bg: "var(--c-ev-mocked-bg)", fg: "var(--c-ev-mocked-fg)", text: "Stop" },
};

export function OutcomeBadge({ outcome, large = false }: { outcome: GateOutcome; large?: boolean }) {
  const s = OUTCOME_STYLE[outcome];
  return (
    <span className={`inline-flex items-center rounded font-semibold ${large ? "px-2.5 py-1 text-base" : "px-1.5 py-0.5 t-micro"}`}
      style={{ background: s.bg, color: s.fg }}>
      {s.text}
    </span>
  );
}

export function MockedLabel({ text = "MOCKED" }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 t-micro font-semibold"
      style={{ background: "var(--c-ev-mocked-bg)", color: "var(--c-ev-mocked-fg)" }}>
      <FlaskConical className="size-3.5" aria-hidden />
      {text}
    </span>
  );
}
