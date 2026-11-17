import { Send } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { Button } from "../ui/Button";

export function Composer({ onSend, busy, disabled, placeholder, suggestion, disabledReason }: {
  onSend: (text: string) => Promise<boolean>; busy: boolean; disabled?: boolean; placeholder: string;
  suggestion?: string | null; disabledReason?: string;
}) {
  const [text, setText] = useState("");
  const send = async () => {
    const value = text.trim();
    if (!value || busy || disabled) return;
    if (await onSend(value)) setText("");
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); }
  };
  return (
    <div className="space-y-2">
      {suggestion && !disabled ? (
        <button type="button" onClick={() => setText(suggestion)}
          className="block w-full rounded-md border border-dashed border-control px-3 py-2 text-left t-small text-muted hover:text-ink hover:bg-sunken">
          <span className="font-medium text-ink">Demo script:</span> {suggestion}
        </button>
      ) : null}
      <div className="flex items-end gap-2 rounded-xl border border-control bg-surface p-2 focus-within:outline-2 focus-within:outline-[var(--c-focus)]">
        <label className="sr-only" htmlFor="composer">Message</label>
        <textarea id="composer" rows={2} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey}
          disabled={disabled} placeholder={disabled ? disabledReason : placeholder}
          className="min-h-[3rem] flex-1 resize-none bg-transparent px-2 py-1.5 outline-none disabled:cursor-not-allowed" />
        <Button variant="primary" onClick={send} busy={busy} disabled={disabled || !text.trim()} icon={<Send className="size-4" aria-hidden />}>
          Send
        </Button>
      </div>
    </div>
  );
}
