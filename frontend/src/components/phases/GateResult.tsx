import { CircleCheck, CircleX } from "lucide-react";
import type { Gate } from "../../types/api";
import { MockedLabel, OutcomeBadge } from "../ui/Badges";

export function GateResult({ gate }: { gate: Gate }) {
  return (
    <div className="space-y-4 rounded-lg border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <OutcomeBadge outcome={gate.outcome} large />
        <p className="font-medium">{gate.reasoning}</p>
      </div>
      <p className="t-micro text-muted flex flex-wrap items-center gap-2">
        Decided by deterministic rules on {new Date(gate.created_at).toLocaleString()}. Evidence basis: {gate.evidence_basis.replace(/_/g, " ")}.
        {gate.evidence_basis === "mocked" ? <MockedLabel text="MOCKED basis" /> : null}
      </p>
      <ul className="divide-y divide-line">
        {gate.checks.map((c) => (
          <li key={c.id} className="flex gap-2.5 py-2 t-small">
            {c.passed ? <CircleCheck className="mt-0.5 size-4 shrink-0 text-accent" aria-label="Passed" /> : <CircleX className="mt-0.5 size-4 shrink-0 text-danger" aria-label="Failed" />}
            <div className="min-w-0">
              <p className="font-medium">{c.label}{c.severity === "hard_policy" ? <span className="ml-2 t-micro text-muted">hard rule</span> : c.severity === "advisory" ? <span className="ml-2 t-micro text-muted">advisory</span> : null}</p>
              <p className="text-muted">{c.detail}</p>
            </div>
          </li>
        ))}
      </ul>
      {gate.commentary ? (
        <div className="border-t border-line pt-3">
          <p className="t-micro font-semibold text-muted">Gatekeeper commentary. Explains the result; cannot change it.</p>
          <p className="t-small mt-1 whitespace-pre-line">{gate.commentary}</p>
        </div>
      ) : null}
    </div>
  );
}
