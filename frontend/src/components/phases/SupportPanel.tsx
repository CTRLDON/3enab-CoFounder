import { useState } from "react";
import { useAction, useResource } from "../../hooks/useResource";
import { api } from "../../services/api";
import type { Venture } from "../../types/api";
import { MockedLabel } from "../ui/Badges";
import { Button } from "../ui/Button";
import { ErrorNotice } from "../ui/Feedback";
import { TextArea, TextField } from "../ui/Fields";

export function SupportPanel({ venture, demoTicket }: { venture: Venture; demoTicket?: { subject: string; body: string } | null }) {
  const tickets = useResource(() => api.tickets(venture.id), [venture.id]);
  const action = useAction();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const source = venture.mode === "demo" ? "mocked" : "founder_entered";
  const submit = async () => {
    const ok = await action.run("ticket", () => api.createTicket(venture.id, subject, body, source));
    if (ok) { setSubject(""); setBody(""); await tickets.reload(); }
  };
  return (
    <div className="space-y-4 rounded-lg border border-line bg-surface p-4">
      <p className="t-small text-muted">Enter a support request you received. Mate categorises it and drafts a reply for you to send yourself. Nothing is sent automatically.</p>
      <div className="grid gap-3">
        <TextField label="Subject" value={subject} onChange={setSubject} />
        <TextArea label="Message" value={body} onChange={setBody} rows={3} />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" disabled={!subject || !body || venture.state !== "OPERATING"} busy={action.busy === "ticket"} onClick={submit}>Triage request</Button>
          {demoTicket ? <Button size="sm" variant="ghost" onClick={() => { setSubject(demoTicket.subject); setBody(demoTicket.body); }}>Use the demo ticket</Button> : null}
        </div>
      </div>
      <ErrorNotice error={action.error} />
      {tickets.data?.map((t) => (
        <div key={t.id} className="border-t border-line pt-3 t-small space-y-1">
          <p className="flex items-center gap-2 font-medium">{t.subject} {t.labels.includes("MOCKED") ? <MockedLabel /> : null}</p>
          <p className="text-muted">Category: {t.category ?? "not triaged"}</p>
          {t.draft_reply ? <p className="rounded-md bg-sunken p-2.5 whitespace-pre-line">{t.draft_reply}</p> : null}
        </div>
      ))}
    </div>
  );
}
