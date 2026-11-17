import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { STATE_LABEL } from "../app/stateLabels";
import { Button } from "../components/ui/Button";
import { ErrorNotice, Loading } from "../components/ui/Feedback";
import { useAction } from "../hooks/useResource";
import { applyTheme } from "../hooks/useVentureTheme";
import { ApiError, api } from "../services/api";
import { getToken, setToken } from "../services/session";
import type { Founder, VentureState } from "../types/api";
import { Onboarding } from "./Onboarding";

export function Home() {
  const navigate = useNavigate();
  const [founder, setFounder] = useState<Founder | null>(null);
  const [ventures, setVentures] = useState<{ id: string; title: string; state: string; mode: string; created_at: string }[]>([]);
  const [checking, setChecking] = useState(Boolean(getToken()));
  const action = useAction();

  useEffect(() => { applyTheme(null); }, []);
  useEffect(() => {
    if (!getToken()) return;
    Promise.all([api.me(), api.ventures()]).then(
      ([f, v]) => { setFounder(f); setVentures(v); setChecking(false); },
      (err) => {
        if (err instanceof ApiError && err.status === 401) setToken(null);
        setChecking(false);
      },
    );
  }, []);

  if (checking) return <div className="p-10"><Loading /></div>;
  if (!founder) return <Onboarding />;

  const start = async (mode: "live" | "demo", scenario?: string) => {
    const v = await action.run(mode + (scenario ?? ""), async () => {
      const venture = await api.createVenture(mode, scenario);
      try { await api.discovery(venture.id); } catch { /* shown on the discussion page */ }
      return venture;
    });
    if (v) navigate(`/v/${v.id}/discuss`);
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <p className="font-semibold tracking-tight text-[1.07rem]">Mate</p>
      <h1 className="t-title mt-10">Welcome back, {founder.display_name}.</h1>
      <p className="mt-2 text-muted">Your profile is saved. Pick up a venture or start a new discussion.</p>
      <ErrorNotice error={action.error} />
      <div className="mt-6 flex flex-wrap gap-2">
        <Button variant="primary" busy={action.busy === "live"} onClick={() => start("live")}>New venture with the live model</Button>
        <Button busy={action.busy === "demomain"} onClick={() => start("demo", "main")}>Scripted demo</Button>
        <Button busy={action.busy === "demoweak"} onClick={() => start("demo", "weak")}>Scripted demo: an idea that should stop</Button>
      </div>
      <h2 className="t-section mt-12">Your ventures</h2>
      {ventures.length ? (
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {ventures.map((v) => (
            <li key={v.id}>
              <Link to={`/v/${v.id}`} className="flex items-baseline justify-between gap-4 py-3 hover:bg-sunken px-2 -mx-2 rounded">
                <span className="font-medium">{v.title}</span>
                <span className="t-small text-muted">{STATE_LABEL[v.state as VentureState] ?? v.state}{v.mode === "demo" ? ", scripted demo" : ""}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : <p className="mt-3 t-small text-muted">No ventures yet.</p>}
      <button type="button" className="mt-10 t-small text-muted underline underline-offset-2"
        onClick={() => { setToken(null); window.location.assign("/"); }}>
        Use a different founder profile on this browser
      </button>
    </div>
  );
}
