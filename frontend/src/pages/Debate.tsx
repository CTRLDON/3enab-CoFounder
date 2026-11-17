import { FileText, Scale, OctagonX } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useVenture } from "../app/ventureContext";
import { Composer } from "../components/chat/Composer";
import { MessageList } from "../components/chat/MessageList";
import { TrackingRail, latestReadiness } from "../components/chat/TrackingRail";
import { Button } from "../components/ui/Button";
import { ErrorNotice, Loading, Skeleton } from "../components/ui/Feedback";
import { useAction, useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { ChatMessage, DemoScenarios, Opportunity } from "../types/api";

export function Debate() {
  const { venture, setVenture, reload } = useVenture();
  const navigate = useNavigate();
  const convo = useResource(() => api.conversation(venture.id), [venture.id]);
  const action = useAction();
  const [comparison, setComparison] = useState<Opportunity[] | null>(null);
  const [demo, setDemo] = useState<DemoScenarios | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    if (venture.mode === "demo") api.demoScenarios().then(setDemo, () => setDemo(null));
  }, [venture.mode]);
  useEffect(() => {
    api.artifacts(venture.id).then(async (list) => {
      const latest = [...list].reverse().find((a) => a.kind === "opportunity_comparison");
      if (latest) {
        const full = await api.artifact(venture.id, latest.id);
        setComparison((full.meta.opportunities as Opportunity[]) ?? null);
      }
    }, () => undefined);
  }, [venture.id]);

  const messages: ChatMessage[] = convo.data?.messages ?? [];
  const awaiting = venture.proposals.find((p) => p.status === "awaiting");
  const canTalk = venture.state === "DISCOVERY" || venture.state === "DEBATE";
  const readiness = latestReadiness(messages);
  const ready = readiness ? Object.entries(readiness).filter(([k]) => k !== "missing").every(([, v]) => v) : false;

  const script = demo?.scenarios[venture.demo_scenario ?? "main"]?.script;
  const founderTurns = messages.filter((m) => m.role === "founder").length;
  const suggestion = venture.mode === "demo" && script ? script.debate[founderTurns] ?? null : null;

  const send = async (text: string) => {
    setPending(text);
    const result = await action.run("send", () => api.debate(venture.id, text));
    setPending(null);
    if (!result) { await convo.reload(); return false; }
    convo.setData({ messages: [...messages, result.founder_message, result.reply] });
    setVenture(result.venture);
    return true;
  };

  const draft = async () => {
    const result = await action.run("proposal", () => api.requestProposal(venture.id));
    if (result) { setVenture(result.venture); navigate(`/v/${venture.id}/proposal/${result.proposal.id}`); }
  };
  const compare = async () => {
    const result = await action.run("compare", () => api.compare(venture.id));
    if (result) { setComparison(result.opportunities); await convo.reload(); }
  };
  const stop = async () => {
    if (!window.confirm("Stop this venture? The discussion and evidence stay on record, and you can reopen it later.")) return;
    const result = await action.run("stop", () => api.stop(venture.id, "Founder chose to stop during the discussion."));
    if (result) setVenture(result);
  };
  const retryDiscovery = async () => {
    const result = await action.run("discovery", () => api.discovery(venture.id));
    if (result) setVenture(result.venture);
  };
  const reopen = async () => {
    const result = await action.run("reopen", () => api.reopen(venture.id, "Founder reopened the discussion."));
    if (result) { setVenture(result); await convo.reload(); }
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-10 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_300px]">
      <section aria-label="Discussion with Mate" className="min-w-0">
        {venture.state === "ONBOARDING" ? (
          <div className="mb-6 space-y-3">
            <ErrorNotice error={action.error ?? new Error("Mate has not analysed your profile yet.")}>
              <Button className="mt-3" size="sm" variant="primary" busy={action.busy === "discovery"} onClick={retryDiscovery}>Analyse my profile</Button>
            </ErrorNotice>
          </div>
        ) : null}

        {awaiting ? (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-accent bg-accent-soft p-4">
            <p><span className="font-semibold">Proposal #{awaiting.number} is waiting for your decision.</span> <span className="text-muted">{awaiting.data.business_name}</span></p>
            <Link to={`/v/${venture.id}/proposal/${awaiting.id}`} className="inline-flex h-9 items-center rounded-md bg-accent px-3 font-medium text-on-accent hover:bg-accent-hover">Review proposal</Link>
          </div>
        ) : null}
        {venture.state === "STOPPED" || venture.state === "PIVOT_REQUIRED" ? (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface p-4">
            <p>
              <span className="font-semibold">{venture.state === "STOPPED" ? "This venture is stopped." : "A pivot is required."}</span>{" "}
              <span className="text-muted">{venture.transitions.at(-1)?.reason}</span>
            </p>
            <Button size="sm" busy={action.busy === "reopen"} onClick={reopen}>Reopen the discussion</Button>
          </div>
        ) : null}
        {venture.plan_version && !canTalk && !awaiting && venture.state !== "STOPPED" && venture.state !== "PIVOT_REQUIRED" ? (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface p-4">
            <p className="font-medium">You approved a plan. This discussion is kept for reference.</p>
            <Link to={`/v/${venture.id}/map`} className="inline-flex h-9 items-center rounded-md bg-accent px-3 font-medium text-on-accent">Open the business map</Link>
          </div>
        ) : null}

        {convo.loading && !convo.data ? <Skeleton lines={4} /> : null}
        <ErrorNotice error={convo.error} onRetry={convo.reload} />
        {messages.length === 0 && !convo.loading && canTalk ? (
          <div className="mb-8">
            <h1 className="t-title">Tell Mate what you want to build.</h1>
            <p className="mt-2 measure text-muted">
              Start with your idea as you'd say it out loud. Mate will ask the question that matters most first, name the
              assumptions it hears, and say plainly when something doesn't add up.
            </p>
          </div>
        ) : null}

        <MessageList messages={pending ? [...messages, { id: -1, role: "founder", agent: null, content: pending, structured: null, created_at: "" }] : messages} ventureId={venture.id} />
        {action.busy === "send" ? <div className="mt-6"><Loading label={venture.mode === "demo" ? "Loading the scripted reply" : "Mate is thinking it through"} /></div> : null}

        <div className="sticky bottom-0 mt-8 space-y-3 bg-bg pb-6 pt-3">
          <ErrorNotice error={action.error && venture.state !== "ONBOARDING" ? action.error : null} />
          <Composer onSend={send} busy={action.busy === "send"} disabled={!canTalk}
            disabledReason={awaiting ? "Decide on the proposal first." : "The discussion is closed in this state."}
            placeholder="Reply to Mate" suggestion={suggestion} />
          {canTalk ? (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant={ready ? "primary" : "secondary"} icon={<FileText className="size-4" aria-hidden />}
                busy={action.busy === "proposal"} disabled={founderTurns === 0} onClick={draft}>Draft a proposal</Button>
              <Button size="sm" icon={<Scale className="size-4" aria-hidden />} busy={action.busy === "compare"} disabled={founderTurns === 0} onClick={compare}>
                Compare directions
              </Button>
              <Button size="sm" variant="ghost" icon={<OctagonX className="size-4" aria-hidden />} busy={action.busy === "stop"} onClick={stop}>Stop here</Button>
            </div>
          ) : null}
        </div>
      </section>
      <aside className="lg:sticky lg:top-28 lg:max-h-[calc(100vh-8rem)] lg:self-start lg:overflow-y-auto lg:pr-1" aria-label="What Mate is tracking">
        <TrackingRail messages={messages} comparison={comparison} />
        <button type="button" className="mt-8 t-micro text-muted underline underline-offset-2" onClick={() => void reload()}>Refresh</button>
      </aside>
    </div>
  );
}
