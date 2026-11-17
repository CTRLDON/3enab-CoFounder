import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSearchParams } from "react-router";
import { useVenture } from "../app/ventureContext";
import { MockedLabel } from "../components/ui/Badges";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorNotice, Skeleton } from "../components/ui/Feedback";
import { useAction, useResource } from "../hooks/useResource";
import { api } from "../services/api";
import type { Artifact } from "../types/api";

function Body({ artifact }: { artifact: Artifact }) {
  if (artifact.content_type === "markdown") {
    return <div className="prose-mate"><ReactMarkdown remarkPlugins={[remarkGfm]}>{String(artifact.content)}</ReactMarkdown></div>;
  }
  if (artifact.content_type === "html") {
    return (
      <iframe title={artifact.title} sandbox="allow-scripts" srcDoc={String(artifact.content)}
        className="h-[70vh] w-full rounded-lg border border-line bg-white" />
    );
  }
  if (artifact.content_type === "bundle" && typeof artifact.content === "object") {
    const files = artifact.content as Record<string, string>;
    return (
      <div className="space-y-3">
        {Object.entries(files).map(([name, text]) => (
          <details key={name} className="rounded-lg border border-line bg-surface">
            <summary className="cursor-pointer px-3 py-2 t-small font-medium">{name}</summary>
            <pre className="max-h-96 overflow-auto border-t border-line bg-sunken p-3 text-[0.78rem] leading-relaxed">{text}</pre>
          </details>
        ))}
      </div>
    );
  }
  let pretty = String(artifact.content);
  try { pretty = JSON.stringify(JSON.parse(pretty), null, 2); } catch { /* keep raw */ }
  return <pre className="max-h-[70vh] overflow-auto rounded-lg bg-sunken p-4 text-[0.8rem] leading-relaxed">{pretty}</pre>;
}

export function Artifacts() {
  const { venture } = useVenture();
  const [params, setParams] = useSearchParams();
  const list = useResource(() => api.artifacts(venture.id), [venture.id]);
  const [current, setCurrent] = useState<Artifact | null>(null);
  const load = useAction();
  const id = params.get("id") ?? list.data?.at(-1)?.id ?? null;

  useEffect(() => {
    if (!id) return;
    void load.run("load", async () => setCurrent(await api.artifact(venture.id, id)));
  }, [id, venture.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = async () => {
    if (!current) return;
    const blob = await api.exportBundle(venture.id, current.id);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `mvp-${current.id}.zip`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const grouped = new Map<number, typeof list.data>();
  (list.data ?? []).forEach((a) => grouped.set(a.phase, [...(grouped.get(a.phase) ?? []), a]));

  return (
    <div className="mx-auto grid max-w-7xl gap-8 px-6 py-10 lg:grid-cols-[260px_minmax(0,1fr)]">
      <nav aria-label="Artifacts" className="space-y-6">
        <h1 className="t-title">Artifacts</h1>
        {list.loading ? <Skeleton /> : null}
        <ErrorNotice error={list.error} onRetry={list.reload} />
        {list.data && !list.data.length ? <EmptyState title="Nothing generated yet" /> : null}
        {[...grouped.entries()].map(([phase, items]) => (
          <div key={phase}>
            <p className="t-micro font-semibold text-muted">Phase {phase}</p>
            <ul className="mt-1.5 space-y-0.5">
              {items?.map((a) => (
                <li key={a.id}>
                  <button type="button" onClick={() => setParams({ id: a.id })}
                    className={`w-full rounded-md px-2 py-1.5 text-left t-small ${a.id === id ? "bg-accent-soft text-accent-text font-medium" : "hover:bg-sunken"}`}>
                    {a.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <section aria-live="polite" className="min-w-0">
        {load.busy ? <Skeleton lines={6} /> : null}
        <ErrorNotice error={load.error} />
        {current && !load.busy ? (
          <article className="space-y-4">
            <header className="flex flex-wrap items-center gap-2">
              <h2 className="t-section mr-2">{current.title}</h2>
              {current.labels.map((l) => (l.includes("MOCKED") || l.includes("DEMO") ? <MockedLabel key={l} text={l} /> :
                <span key={l} className="rounded bg-sunken px-1.5 py-0.5 t-micro">{l.toLowerCase()}</span>))}
              {current.content_type === "bundle" ? <Button size="sm" icon={<Download className="size-4" aria-hidden />} onClick={download}>Download the MVP</Button> : null}
            </header>
            {current.content_type === "html" ? <p className="t-micro text-muted">Shown in a sandboxed frame with no network access. Draft pages are never published.</p> : null}
            <Body artifact={current} />
          </article>
        ) : null}
      </section>
    </div>
  );
}
