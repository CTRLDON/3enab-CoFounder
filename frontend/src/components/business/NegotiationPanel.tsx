import { useEffect, useState } from "react";
import { useVenture } from "../../app/ventureContext";
import { useAction } from "../../hooks/useResource";
import { api } from "../../services/api";
import type { DemoScenarios, Negotiation, Plan, PlanNode } from "../../types/api";
import { Composer } from "../chat/Composer";
import { MessageList } from "../chat/MessageList";
import { Button } from "../ui/Button";
import { ErrorNotice, Loading } from "../ui/Feedback";
import { RevisionDiff } from "./RevisionDiff";

export function NegotiationPanel({ node, plan, onPlanChanged, onClose }: {
  node: PlanNode; plan: Plan; onPlanChanged: (plan: Plan) => void; onClose: () => void;
}) {
  const { venture } = useVenture();
  const action = useAction();
  const [session, setSession] = useState<Negotiation | null>(null);
  const [demo, setDemo] = useState<DemoScenarios | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);

  useEffect(() => {
    setSession(null);
    setOutcome(null);
    const open = plan.open_negotiations.find((n) => n.node_id === node.id);
    if (open) api.negotiation(venture.id, open.id).then(setSession, () => undefined);
    if (venture.mode === "demo") api.demoScenarios().then(setDemo, () => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.id, venture.id]);

  const script = demo?.scenarios[venture.demo_scenario ?? "main"]?.script;
  const founderTurns = session?.messages.filter((m) => m.role === "founder").length ?? 0;
  const suggestion = script && script.negotiation_node === node.id ? script.negotiation[founderTurns] ?? null : null;

  const send = async (text: string) => {
    const result = await action.run("send", () =>
      session ? api.negotiate(venture.id, session.id, text) : api.openNegotiation(venture.id, node.id, text));
    if (result) setSession(result);
    return Boolean(result);
  };

  const decide = async (decision: "approve" | "reject") => {
    if (!session) return;
    const result = await action.run(decision, () => api.decideNegotiation(venture.id, session.id, decision, session.base_version));
    if (!result) return;
    setSession(result.negotiation);
    onPlanChanged(result.plan);
    setOutcome(decision === "approve" ? `Saved as plan v${result.plan.current_version}.` : "Rejected. The plan is unchanged.");
  };

  const closed = session && ["approved", "rejected", "conflict"].includes(session.status);

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-1 border-b border-line px-5 py-4">
        <p className="t-micro text-muted">Propose a change</p>
        <h2 className="t-section">{node.title}</h2>
        <p className="t-micro text-muted">Mate will weigh the change against the rest of the plan. Nothing changes until you approve a revision.</p>
      </div>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
        {session ? <MessageList messages={session.messages} compact /> : (
          <p className="t-small text-muted">Describe what you want to change and why. For example: “Replace the subscription with a one-time price.”</p>
        )}
        {action.busy === "send" ? <Loading label={venture.mode === "demo" ? "Loading the scripted reply" : "Mate is weighing the change"} /> : null}
        {session?.status === "proposed" && session.proposed_change ? (
          <section className="rounded-lg border border-line bg-surface p-4" aria-label="Proposed revision">
            <p className="font-semibold mb-3">Revision ready for your decision</p>
            <RevisionDiff revision={session.proposed_change} nodes={plan.document.nodes} />
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" busy={action.busy === "approve"} onClick={() => decide("approve")}>Approve this revision</Button>
              <Button size="sm" busy={action.busy === "reject"} onClick={() => decide("reject")}>Reject, keep the current plan</Button>
            </div>
            <p className="t-micro text-muted mt-2">Based on plan v{session.base_version}. If the plan changed since, Mate will refuse to overwrite it.</p>
          </section>
        ) : null}
        {outcome ? <p role="status" className="rounded-md bg-accent-soft px-3 py-2 t-small text-accent-text">{outcome}</p> : null}
        <ErrorNotice error={action.error} />
      </div>
      <div className="border-t border-line px-5 py-4">
        {closed ? (
          <Button size="sm" onClick={onClose}>Back to the node</Button>
        ) : (
          <Composer onSend={send} busy={action.busy === "send"} placeholder={`What should change in “${node.title}”?`} suggestion={suggestion} />
        )}
      </div>
    </div>
  );
}
