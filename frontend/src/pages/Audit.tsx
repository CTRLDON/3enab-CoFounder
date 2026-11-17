import { useState } from "react";
import { useVenture } from "../app/ventureContext";
import { OutcomeBadge } from "../components/ui/Badges";
import { ErrorNotice, Skeleton } from "../components/ui/Feedback";
import { Tabs } from "../components/ui/Tabs";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { GateOutcome } from "../types/api";

export function Audit() {
  const { venture } = useVenture();
  const data = useResource(() => api.audit(venture.id), [venture.id]);
  const [tab, setTab] = useState("events");
  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="t-title">Decision log</h1>
      <p className="mt-2 measure text-muted">Every agent action, approval, gate and state change, as written to decision_log.json.</p>
      {data.data ? <p className="t-micro text-muted mt-2">{data.data.cost_note}</p> : null}
      <div className="mt-6"><Tabs label="Log views" value={tab} onChange={setTab} items={[{ id: "events", label: "Actions" }, { id: "runs", label: "Agent runs" }, { id: "states", label: "State changes" }]} /></div>
      {data.loading ? <div className="mt-6"><Skeleton lines={6} /></div> : null}
      <ErrorNotice error={data.error} onRetry={data.reload} />
      {tab === "events" && data.data ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full t-small">
            <thead><tr className="text-left text-muted">{["Time", "Agent", "Action", "Model", "Cost (USD)", "Approved by", "Outcome", "Mode"].map((h) => <th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {data.data.events.map((e) => (
                <tr key={e.id} className="border-t border-line align-top">
                  <td className="px-2 py-2 whitespace-nowrap tabular-nums text-muted">{new Date(e.timestamp).toLocaleTimeString()}</td>
                  <td className="px-2 py-2">{e.agent.replace(/_/g, " ")}</td>
                  <td className="px-2 py-2 break-all">{e.action}{e.sources.length ? <span className="block t-micro text-muted">{e.sources.length} source(s)</span> : null}</td>
                  <td className="px-2 py-2">{e.model ?? <span className="text-muted">none</span>}</td>
                  <td className="px-2 py-2 tabular-nums">{e.cost.toFixed(2)}</td>
                  <td className="px-2 py-2">{e.approved_by ?? <span className="text-muted">—</span>}</td>
                  <td className="px-2 py-2">{e.outcome ? <OutcomeBadge outcome={e.outcome.toUpperCase() as GateOutcome} /> : null}</td>
                  <td className="px-2 py-2 text-muted">{e.execution_mode.replace(/_/g, " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {tab === "runs" && data.data ? (
        <ul className="mt-4 divide-y divide-line">
          {data.data.agent_runs.map((r) => (
            <li key={r.id} className="py-2.5 t-small">
              <p><span className="font-medium">{r.agent.replace(/_/g, " ")}</span> {r.task.replace(/_/g, " ")} <span className={r.status === "failed" ? "text-danger" : "text-muted"}>{r.status}</span></p>
              <p className="t-micro text-muted">
                {r.model ?? "no model"}, {r.execution_mode.replace(/_/g, " ")}, {r.attempts} attempt(s), {r.duration_ms} ms
                {r.prompt_tokens ? `, ${r.prompt_tokens}+${r.completion_tokens} tokens` : ""}
              </p>
              {r.error ? <p className="t-micro text-danger mt-1">{r.error}</p> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {tab === "states" ? (
        <ol className="mt-4 space-y-3">
          {venture.transitions.map((t, i) => (
            <li key={i} className="t-small">
              <p><span className="font-medium">{t.from} to {t.to}</span> <span className="text-muted">by {t.actor}</span></p>
              <p className="text-muted">{t.reason}</p>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
