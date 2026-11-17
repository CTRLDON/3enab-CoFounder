import { Lock } from "lucide-react";
import { useState } from "react";
import { useAction } from "../../hooks/useResource";
import { api } from "../../services/api";
import type { Experiment, Venture } from "../../types/api";
import { MockedLabel } from "../ui/Badges";
import { Button } from "../ui/Button";
import { ErrorNotice } from "../ui/Feedback";
import { SelectField, TextField } from "../ui/Fields";

export function ExperimentPanel({ venture, experiments, onChange, demoResult }: {
  venture: Venture; experiments: Experiment[]; onChange: () => void; demoResult?: { observed: number; note: string } | null;
}) {
  const action = useAction();
  const [observed, setObserved] = useState<Record<string, string>>({});
  const [source, setSource] = useState<"founder_reported" | "mocked">(venture.mode === "demo" ? "mocked" : "founder_reported");
  const [note, setNote] = useState("");
  const canRecord = venture.state === "VALIDATING" || venture.state === "OPERATING";

  const record = async (exp: Experiment) => {
    const value = Number(observed[exp.id]);
    if (Number.isNaN(value) || observed[exp.id] === undefined || observed[exp.id] === "") return;
    const ok = await action.run(exp.id, () => api.recordResult(venture.id, exp.id, value, source, note));
    if (ok) { setObserved({ ...observed, [exp.id]: "" }); setNote(""); onChange(); }
  };

  if (!experiments.length) return <p className="t-small text-muted">Experiments are declared when Phase 2 runs.</p>;
  return (
    <div className="space-y-4">
      {experiments.map((exp) => {
        const latest = exp.results.at(-1);
        const ratio = latest ? latest.observed / exp.target : null;
        return (
          <div key={exp.id} className="rounded-lg border border-line bg-surface p-4 space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-semibold">{exp.name}</p>
              <p className="inline-flex items-center gap-1 t-micro text-muted"><Lock className="size-3" aria-hidden />Target locked before results</p>
            </div>
            <p className="t-small">Target: <span className="font-semibold tabular-nums">{exp.target} {exp.metric}</span> within {exp.window_days} days.</p>
            {latest ? (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 t-small">
                  <span>Latest recorded: <span className="font-semibold tabular-nums">{latest.observed}</span> ({Math.round((ratio ?? 0) * 100)}% of target)</span>
                  {latest.source === "mocked" ? <MockedLabel /> : <span className="t-micro text-muted">founder-reported</span>}
                </div>
                <div className="h-2 rounded-full bg-sunken" aria-hidden>
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, (ratio ?? 0) * 100)}%`, background: (ratio ?? 0) >= 1 ? "var(--c-accent)" : "var(--c-econ-expense)" }} />
                </div>
                {latest.note ? <p className="t-micro text-muted">{latest.note}</p> : null}
              </div>
            ) : <p className="t-small text-muted">No result recorded. The gate treats this as pending; nothing is assumed.</p>}
            {canRecord ? (
              <div className="grid items-end gap-3 sm:grid-cols-[120px_1fr_auto]">
                <TextField label="Observed" type="number" value={observed[exp.id] ?? ""} onChange={(v) => setObserved({ ...observed, [exp.id]: v })} />
                <TextField label="Note or source" value={note} onChange={setNote} placeholder="Where does this number come from?" />
                <Button busy={action.busy === exp.id} onClick={() => record(exp)}>Record result</Button>
              </div>
            ) : null}
            {canRecord && venture.mode === "demo" ? (
              <div className="flex flex-wrap items-end gap-3">
                <SelectField label="Result source" value={source} onChange={setSource}
                  options={[{ value: "mocked", label: "MOCKED demo input" }, { value: "founder_reported", label: "Founder-reported" }]} />
                {demoResult ? (
                  <Button size="sm" variant="ghost" onClick={() => { setObserved({ ...observed, [exp.id]: String(demoResult.observed) }); setNote(demoResult.note); }}>
                    Use the demo script value
                  </Button>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
      <ErrorNotice error={action.error} />
    </div>
  );
}
