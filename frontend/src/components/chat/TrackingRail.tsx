import { Circle, CircleCheck } from "lucide-react";
import type { Assumption, ChatMessage, Opportunity, Readiness } from "../../types/api";
import { EvidenceBadge } from "../ui/Badges";

const READINESS_LABELS: [keyof Omit<Readiness, "missing">, string][] = [
  ["problem_defined", "A specific problem"],
  ["customer_defined", "A specific customer"],
  ["founder_fit_assessed", "Fit with your resources"],
  ["differentiation_identified", "A reason to choose it"],
  ["feasible_with_resources", "Feasible with your budget and time"],
  ["first_experiment_identified", "A first cheap experiment"],
];

export function latestReadiness(messages: ChatMessage[]): Readiness | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const r = messages[i].structured?.readiness;
    if (r && messages[i].agent === "skeptical_cofounder") return r;
  }
  return null;
}

export function TrackingRail({ messages, comparison }: { messages: ChatMessage[]; comparison: Opportunity[] | null }) {
  const readiness = latestReadiness(messages);
  const seen = new Map<string, Assumption>();
  messages.forEach((m) => m.structured?.assumptions?.forEach((a) => seen.set(a.statement, a)));
  const assumptions = [...seen.values()].slice(-8);
  return (
    <div className="space-y-8">
      <section aria-labelledby="readiness-h">
        <h2 id="readiness-h" className="t-small font-semibold">Ready for a proposal?</h2>
        <p className="t-micro text-muted mt-0.5">Mate proposes when these are established, or when you ask.</p>
        <ul className="mt-3 space-y-1.5">
          {READINESS_LABELS.map(([key, label]) => {
            const ok = readiness?.[key] ?? false;
            return (
              <li key={key} className={`flex items-center gap-2 t-small ${ok ? "" : "text-muted"}`}>
                {ok ? <CircleCheck className="size-4 text-accent" aria-hidden /> : <Circle className="size-4" aria-hidden />}
                <span>{label}</span><span className="sr-only">{ok ? "established" : "not yet"}</span>
              </li>
            );
          })}
        </ul>
        {readiness?.missing?.length ? <p className="t-micro text-muted mt-3">Still missing: {readiness.missing.join("; ")}.</p> : null}
      </section>

      {comparison ? (
        <section aria-labelledby="comparison-h">
          <h2 id="comparison-h" className="t-small font-semibold">Directions compared</h2>
          <p className="t-micro text-muted mt-0.5">Heuristic index from 12 weighted criteria. Not a probability of success.</p>
          <ul className="mt-3 space-y-3">
            {comparison.map((o) => (
              <li key={o.key}>
                <div className="flex items-baseline justify-between gap-2 t-small">
                  <span className="font-medium">{o.title}</span>
                  <span className="tabular-nums">{o.heuristic_index}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-sunken" aria-hidden>
                  <div className="h-full rounded-full bg-accent" style={{ width: `${o.heuristic_index}%` }} />
                </div>
                <p className="t-micro text-muted mt-1">{o.main_uncertainty} Budget: {o.budget_check.replace(/_/g, " ")}.</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="assumptions-h">
        <h2 id="assumptions-h" className="t-small font-semibold">Assumptions on the table</h2>
        <p className="t-micro text-muted mt-0.5">None of these are verified. Mate keeps them visible until evidence arrives.</p>
        {assumptions.length ? (
          <ul className="mt-3 space-y-2.5">
            {assumptions.map((a) => (
              <li key={a.statement} className="flex items-start gap-2">
                <EvidenceBadge value={a.classification} compact />
                <p className="t-small">{a.statement}</p>
              </li>
            ))}
          </ul>
        ) : <p className="t-small text-muted mt-2">Mate lists the assumptions it hears as the discussion goes.</p>}
      </section>
    </div>
  );
}
