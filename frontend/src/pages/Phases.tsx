import { CircleCheck, Lock, OctagonX, Play, Shuffle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useVenture } from "../app/ventureContext";
import { CommercePanel } from "../components/phases/CommercePanel";
import { ExperimentPanel } from "../components/phases/ExperimentPanel";
import { GateResult } from "../components/phases/GateResult";
import { SupportPanel } from "../components/phases/SupportPanel";
import { MockedLabel } from "../components/ui/Badges";
import { Button } from "../components/ui/Button";
import { ErrorNotice, Loading, Skeleton } from "../components/ui/Feedback";
import { useAction, useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { DemoScenarios, PhaseView } from "../types/api";

const RUN_TEXT: Record<number, string> = {
  1: "Research the market and prepare customer interviews",
  2: "Write the Lean Canvas, landing page and experiments",
  3: "Specify, build and test the MVP",
  4: "Propose pricing, costs and draft policies",
  5: "Draft the store page and launch package",
  6: "Read the results and write the persevere-or-pivot memo",
};
const RUN_MARKER: Record<number, string> = {
  1: "evidence_register", 2: "validation_pack", 3: "mvp_test_report", 4: "commercial_pack", 5: "launch_pack", 6: "operations_review",
};
const GATE_TEXT: Record<number, string> = {
  1: "Does the opportunity fit you and justify validation?",
  2: "Did the experiments meet the targets declared in advance?",
  3: "Do the MVP's tests pass and does it match the agreed scope?",
  4: "Have you reviewed and approved the commercial setup?",
  5: "Is the launch package approved and safe within the mocked environment?",
  6: "Continue, repeat an experiment, pivot or stop?",
};

function StatusMark({ status }: { status: PhaseView["status"] }) {
  if (status === "passed") return <CircleCheck className="size-5 text-accent" aria-label="Passed" />;
  if (status === "stop") return <OctagonX className="size-5 text-danger" aria-label="Stopped" />;
  if (status === "pivot") return <Shuffle className="size-5" aria-label="Pivot" />;
  if (status === "locked") return <Lock className="size-5 text-muted" aria-label="Locked" />;
  return <span className="grid size-5 place-items-center rounded-full bg-accent" aria-label="Active"><span className="size-2 rounded-full bg-on-accent" /></span>;
}

export function Phases() {
  const { venture, setVenture } = useVenture();
  const phases = useResource(() => api.phases(venture.id), [venture.id]);
  const action = useAction();
  const [demo, setDemo] = useState<DemoScenarios | null>(null);
  const [openPhases, setOpenPhases] = useState<Record<number, boolean>>({});
  useEffect(() => { if (venture.mode === "demo") api.demoScenarios().then(setDemo, () => undefined); }, [venture.mode]);
  const script = demo?.scenarios[venture.demo_scenario ?? "main"]?.script;

  const refresh = async () => {
    await phases.reload();
    setVenture(await api.venture(venture.id));
  };
  const run = async (n: number) => {
    const r = await action.run(`run-${n}`, () => api.runPhase(venture.id, n));
    if (r) { phases.setData(r.phases); setVenture(r.venture); }
  };
  const gate = async (n: number) => {
    const r = await action.run(`gate-${n}`, () => api.gate(venture.id, n));
    if (r) {
      setOpenPhases((o) => ({ ...o, [n]: true, ...(r.gate.outcome === "GO" && n < 6 ? { [n + 1]: true } : {}) }));
      setVenture(r.venture);
      await phases.reload();
    }
  };
  const approve = async (subject: string, decision: "approve" | "reject") => {
    const r = await action.run(`${subject}-${decision}`, () => api.approve(venture.id, subject, decision));
    if (r) await refresh();
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="t-title">Six phases, each with a gate</h1>
      <p className="mt-2 measure text-muted">
        Agents do the work; gates decide from recorded data and your approvals. The model can explain a gate result but cannot change it.
        A gate can say stop.
      </p>
      <ErrorNotice error={action.error} />
      {phases.loading && !phases.data ? <div className="mt-8"><Skeleton lines={6} /></div> : null}
      <ErrorNotice error={phases.error} onRetry={phases.reload} />

      <ol className="mt-10 space-y-4">
        {phases.data?.map((p) => {
          const active = p.status === "active";
          const ran = p.artifacts.some((a) => a.kind === RUN_MARKER[p.phase]);
          const commercialPack = p.artifacts.find((a) => a.kind === "commercial_pack");
          const launchPack = p.artifacts.find((a) => a.kind === "launch_pack");
          return (
            <li key={p.phase} className={`rounded-xl border bg-surface ${active ? "border-control" : "border-line"}`}>
              <details open={openPhases[p.phase] ?? active} className="group"
                onToggle={(e) => { const isOpen = (e.currentTarget as HTMLDetailsElement).open; setOpenPhases((o) => (o[p.phase] === isOpen ? o : { ...o, [p.phase]: isOpen })); }}>
                <summary className="flex cursor-pointer list-none items-center gap-4 px-5 py-4">
                  <StatusMark status={p.status} />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">Phase {p.phase}: {p.name}</p>
                    <p className="t-small text-muted">{GATE_TEXT[p.phase]}</p>
                  </div>
                  {p.phase === 5 ? <MockedLabel text="MOCKED commerce" /> : null}
                  <span className="t-micro text-muted hidden sm:inline">{p.agents.length} agents</span>
                </summary>
                <div className="space-y-6 border-t border-line px-5 py-5">
                  <p className="t-small text-muted">Agents: {p.agents.map((a) => a.replace(/_/g, " ")).join(", ")}.</p>

                  {active ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <Button variant={ran ? "secondary" : "primary"} icon={<Play className="size-4" aria-hidden />} busy={action.busy === `run-${p.phase}`} onClick={() => run(p.phase)}>
                        {ran ? "Run again" : RUN_TEXT[p.phase]}
                      </Button>
                      <Button variant={ran ? "primary" : "secondary"} busy={action.busy === `gate-${p.phase}`} disabled={!ran} onClick={() => gate(p.phase)}>
                        Evaluate the gate
                      </Button>
                      {action.busy === `run-${p.phase}` ? <Loading label={venture.mode === "demo" ? "Running agents with scripted responses" : "Agents are working with the live model"} /> : null}
                    </div>
                  ) : null}

                  {p.artifacts.length ? (
                    <div>
                      <h3 className="t-small font-semibold">Outputs</h3>
                      <ul className="mt-2 flex flex-wrap gap-2">
                        {p.artifacts.filter((a) => a.kind !== "gate_decision").map((a) => (
                          <li key={a.id}>
                            <Link to={`/v/${venture.id}/artifacts?id=${a.id}`} className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1 t-small hover:border-control">
                              {a.title}
                              {a.labels.filter((l) => l !== "SCRIPTED DEMO").slice(0, 1).map((l) => <span key={l} className="t-micro text-muted">{l.toLowerCase()}</span>)}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {p.phase === 2 ? (
                    <ExperimentPanel venture={venture} experiments={p.experiments} onChange={refresh} demoResult={script?.experiment_results[0] ?? null} />
                  ) : null}

                  {p.phase === 4 && commercialPack && active ? (
                    <div className="flex flex-wrap items-center gap-2 rounded-lg bg-sunken p-4">
                      <p className="t-small flex-1">Review the pricing, cost assumptions and draft policies, then decide. The gate waits for you.</p>
                      <Button size="sm" variant="primary" busy={action.busy === "commercial_setup-approve"} onClick={() => approve("commercial_setup", "approve")}>Approve commercial setup</Button>
                      <Button size="sm" busy={action.busy === "commercial_setup-reject"} onClick={() => approve("commercial_setup", "reject")}>Reject</Button>
                    </div>
                  ) : null}

                  {p.phase === 5 && launchPack && active ? (
                    <div className="flex flex-wrap items-center gap-2 rounded-lg bg-sunken p-4">
                      <p className="t-small flex-1">Approve the store page and announcements. Mate will still not post anything; you post them yourself.</p>
                      <Button size="sm" variant="primary" busy={action.busy === "launch_package-approve"} onClick={() => approve("launch_package", "approve")}>Approve launch package</Button>
                      <Button size="sm" busy={action.busy === "launch_package-reject"} onClick={() => approve("launch_package", "reject")}>Reject</Button>
                    </div>
                  ) : null}
                  {p.phase === 5 && (active || venture.state === "OPERATING") ? <CommercePanel venture={venture} onChange={refresh} /> : null}
                  {p.phase === 6 && active ? <SupportPanel venture={venture} demoTicket={script?.support_ticket ?? null} /> : null}

                  {p.gate ? <GateResult gate={p.gate} /> : null}
                  {p.status === "locked" ? <p className="t-small text-muted">Opens when the previous gate says go.</p> : null}
                </div>
              </details>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
