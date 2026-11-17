import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useVenture } from "../app/ventureContext";
import { EvidenceBadge } from "../components/ui/Badges";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorNotice } from "../components/ui/Feedback";
import { TextArea } from "../components/ui/Fields";
import { useAction } from "../hooks/useResource";
import { api } from "../services/api";
import type { MoneyEstimate } from "../types/api";

const REC_TEXT = {
  PROCEED_TO_VALIDATION: "Proceed to validation",
  VALIDATE_CAREFULLY: "Validate carefully before building",
  DO_NOT_PROCEED: "Mate advises against proceeding",
};

function money(m: MoneyEstimate) {
  return m.amount === null ? "Unknown" : `${m.amount.toLocaleString()} ${m.currency}${m.period ? ` ${m.period}` : ""}`;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-2 border-t border-line py-5 md:grid-cols-[200px_minmax(0,1fr)]">
      <h2 className="t-small font-semibold text-muted">{title}</h2>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

const List = ({ items }: { items: string[] }) => <ul className="list-disc space-y-1 pl-5">{items.map((i) => <li key={i}>{i}</li>)}</ul>;

export function ProposalReview() {
  const { proposalId } = useParams();
  const { venture, setVenture } = useVenture();
  const navigate = useNavigate();
  const action = useAction();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const proposal = venture.proposals.find((p) => p.id === proposalId);
  if (!proposal) return <div className="mx-auto max-w-3xl px-6 py-10"><EmptyState title="Proposal not found" /></div>;
  const p = proposal.data;
  const decidable = proposal.status === "awaiting" && venture.state === "AWAITING_FOUNDER_APPROVAL";

  const decide = async (decision: "approve" | "reject") => {
    const result = await action.run(decision, () => api.decideProposal(venture.id, proposal.id, decision, decision === "reject" ? reason : "Approved in proposal review."));
    if (!result) return;
    setVenture(result.venture);
    navigate(decision === "approve" ? `/v/${venture.id}/map` : `/v/${venture.id}/discuss`, { state: { fromApproval: decision === "approve" } });
  };

  return (
    <div className="mx-auto max-w-4xl px-6 pb-40 pt-10">
      <p className="t-small text-muted">Proposal #{proposal.number}, {proposal.status === "awaiting" ? "waiting for your decision" : proposal.status}</p>
      <h1 className="t-display mt-2">{p.business_name}</h1>
      <p className="mt-3 measure text-[1.07rem]">{p.one_liner}</p>
      <div className="mt-6 flex flex-wrap items-center gap-3 rounded-lg bg-sunken p-4">
        <span className="font-semibold">{REC_TEXT[p.recommendation]}.</span>
        <span className="text-muted">{p.recommended_next_action}</span>
      </div>
      {proposal.policy_findings.length ? (
        <ErrorNotice error={new Error("This proposal falls into an excluded category and cannot be approved.")}>
          <p className="t-small mt-1">{proposal.policy_findings.map((f) => f.message).join(" ")}</p>
        </ErrorNotice>
      ) : null}

      <div className="mt-8">
        <Section title="Problem">{p.problem}</Section>
        <Section title="Target customer">{p.target_customer}</Section>
        <Section title="Solution">{p.solution}</Section>
        <Section title="Founder–idea fit"><p>{p.founder_fit}</p><p className="t-small text-muted mt-1">Heuristic score {p.founder_fit_score} of 5.</p></Section>
        <Section title="Value proposition">{p.value_proposition}</Section>
        <Section title="Business model"><p>{p.business_model}</p><div className="mt-2"><List items={p.revenue_streams} /></div></Section>
        <Section title="Main expenses">
          <ul className="space-y-2">
            {p.main_expenses.map((e) => (
              <li key={e.item} className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{e.item}</span><span className="tabular-nums">{money(e.estimate)}</span>
                <EvidenceBadge value={e.estimate.classification} />
                {e.estimate.basis ? <span className="t-small text-muted w-full">{e.estimate.basis}</span> : null}
              </li>
            ))}
          </ul>
          <p className="mt-3">Start-up capital: <span className="font-medium tabular-nums">{money(p.estimated_startup_capital)}</span> <EvidenceBadge value={p.estimated_startup_capital.classification} /></p>
        </Section>
        <Section title="Competitive alternatives">
          <ul className="space-y-1">{p.competitive_alternatives.map((c) => <li key={c.name}><span className="font-medium">{c.name}</span> <span className="text-muted">{c.note}</span></li>)}</ul>
          <p className="t-micro text-muted mt-2">Named during the discussion. Phase 1 research checks which ones a retrieved source confirms.</p>
        </Section>
        <Section title="Major risks"><List items={p.major_risks} /></Section>
        <Section title="Missing evidence"><List items={p.missing_evidence} /></Section>
        <Section title="First experiment">
          <p className="font-medium">{p.first_experiment.name}</p>
          <p className="mt-1">{p.first_experiment.method}</p>
          <p className="mt-2">Target declared now: <span className="font-semibold tabular-nums">{p.first_experiment.target} {p.first_experiment.metric}</span> within {p.first_experiment.window_days} days.</p>
          {p.first_experiment.threshold_rationale ? <p className="t-small text-muted mt-1">{p.first_experiment.threshold_rationale}</p> : null}
        </Section>
        <Section title="Reasons for"><List items={p.reasons_for} /></Section>
        <Section title="Reasons against"><List items={p.reasons_against} /></Section>
      </div>

      {decidable ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur">
          <div className="mx-auto max-w-4xl space-y-3 px-6 py-4">
            <ErrorNotice error={action.error} />
            {rejecting ? (
              <TextArea label="What should Mate reconsider?" value={reason} onChange={setReason} rows={2}
                hint="Your reason goes back into the discussion. Everything said so far is kept." />
            ) : null}
            <div className="flex flex-wrap gap-3">
              <Button variant="primary" busy={action.busy === "approve"} disabled={Boolean(proposal.policy_findings.length)} onClick={() => decide("approve")}>
                Approve this business direction
              </Button>
              {rejecting ? (
                <Button busy={action.busy === "reject"} onClick={() => decide("reject")}>Send back to the discussion</Button>
              ) : (
                <Button onClick={() => setRejecting(true)}>Continue challenging the idea</Button>
              )}
            </div>
            <p className="t-micro text-muted">Approving creates your business workspace from this proposal. It does not validate anything yet.</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
