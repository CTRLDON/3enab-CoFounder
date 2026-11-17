import { ShieldCheck } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link } from "react-router";
import type { ChatMessage } from "../../types/api";
import { EvidenceBadge } from "../ui/Badges";

export const STANCE_LABEL: Record<string, string> = {
  CHALLENGE: "Challenging",
  PROBE: "Probing",
  AGREE_WITH_CAVEATS: "Agrees, with caveats",
  RECOMMEND_PIVOT: "Recommends a pivot",
  RECOMMEND_STOP: "Recommends stopping",
  AGREE: "Agrees",
  DISAGREE: "Disagrees",
  COUNTER_PROPOSAL: "Counter-proposal",
  NEED_INFO: "Needs more information",
};

function Paragraphs({ text }: { text: string }) {
  return <>{text.split(/\n{2,}/).map((para, i) => <p key={i} className="mt-2 first:mt-0 whitespace-pre-line">{para}</p>)}</>;
}

function AgentMessage({ message, compact }: { message: ChatMessage; compact: boolean }) {
  const s = message.structured ?? {};
  const isPolicy = Boolean(s.policy);
  const stance = s.stance ?? s.position;
  return (
    <article className="fade-in" aria-label={isPolicy ? "Policy guard" : "Mate"}>
      <header className="mb-1.5 flex items-center gap-2 t-micro text-muted">
        {isPolicy ? <ShieldCheck className="size-3.5" aria-hidden /> : <span className="size-1.5 rounded-full bg-accent" aria-hidden />}
        <span className="font-semibold text-ink">{isPolicy ? "Policy guard" : "Mate"}</span>
        {stance ? <span>{STANCE_LABEL[stance] ?? stance}</span> : null}
      </header>
      <div className={compact ? "t-small" : "measure"}>
        <Paragraphs text={message.content} />
      </div>
      {s.key_question ? (
        <p className="mt-3 border-l-2 border-accent pl-3 font-medium">{s.key_question}</p>
      ) : null}
      {!compact && s.assumptions && s.assumptions.length ? (
        <details className="mt-3 group">
          <summary className="cursor-pointer t-small text-muted hover:text-ink">
            {s.assumptions.length} assumption{s.assumptions.length > 1 ? "s" : ""} named in this reply
          </summary>
          <ul className="mt-2 space-y-2">
            {s.assumptions.map((a, i) => (
              <li key={i} className="flex gap-2 t-small">
                <EvidenceBadge value={a.classification} compact />
                <span><span className="text-ink">{a.statement}</span>{a.why_it_matters ? <span className="text-muted"> — {a.why_it_matters}</span> : null}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {!compact && s.alternatives && s.alternatives.length ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {s.alternatives.map((alt) => (
            <div key={alt.title} className="rounded-lg border border-line bg-surface p-3">
              <p className="t-small font-semibold">{alt.title}</p>
              <p className="t-micro text-muted mt-1">{alt.one_liner}</p>
              {alt.why_better_fit ? <p className="t-micro mt-2">{alt.why_better_fit}</p> : null}
            </div>
          ))}
        </div>
      ) : null}
      {s.revision_rejected_by_validator ? (
        <p className="mt-2 t-micro text-danger">Mate's suggested change was invalid and was not offered: {s.revision_rejected_by_validator.join(" ")}</p>
      ) : null}
    </article>
  );
}

export function MessageList({ messages, ventureId, compact = false }: { messages: ChatMessage[]; ventureId?: string; compact?: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length]);
  return (
    <ol className={compact ? "space-y-5" : "space-y-8"} aria-live="polite">
      {messages.map((m) => (
        <li key={m.id}>
          {m.role === "founder" ? (
            <div className="flex justify-end">
              <p className={`max-w-[85%] rounded-2xl rounded-br-md bg-sunken px-4 py-2.5 whitespace-pre-line ${compact ? "t-small" : ""}`}>
                <span className="sr-only">You: </span>{m.content}
              </p>
            </div>
          ) : m.role === "system" ? (
            <p className="text-center t-micro text-muted">
              {m.content}{" "}
              {m.structured?.proposal_id && ventureId && m.structured.kind === "proposal" ? (
                <Link className="text-accent-text underline underline-offset-2" to={`/v/${ventureId}/proposal/${m.structured.proposal_id}`}>Review it</Link>
              ) : null}
            </p>
          ) : (
            <AgentMessage message={m} compact={compact} />
          )}
        </li>
      ))}
      <div ref={end} />
    </ol>
  );
}
