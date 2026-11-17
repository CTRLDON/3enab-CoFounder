import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, useParams } from "react-router";
import { TopBar } from "../components/layout/TopBar";
import { ErrorNotice, Loading } from "../components/ui/Feedback";
import { useVentureTheme } from "../hooks/useVentureTheme";
import { api } from "../services/api";
import type { Venture } from "../types/api";
import { VentureContext } from "./ventureContext";

export function VentureLayout() {
  const { ventureId } = useParams();
  const [venture, setVenture] = useState<Venture | null>(null);
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(async () => {
    if (!ventureId) return null;
    try {
      const v = await api.venture(ventureId);
      setVenture(v);
      setError(null);
      return v;
    } catch (err) {
      setError(err);
      return null;
    }
  }, [ventureId]);

  useEffect(() => { void reload(); }, [reload]);
  const themeKey = venture ? `${venture.state}:${venture.plan_version}:${venture.proposals.length}:${venture.proposals.map((p) => p.status).join()}` : "";
  const theme = useVentureTheme(ventureId, themeKey);
  const value = useMemo(() => (venture ? { venture, setVenture, reload, theme } : null), [venture, reload, theme]);

  if (error && !venture) return <div className="mx-auto max-w-xl p-10"><ErrorNotice error={error} onRetry={reload} /></div>;
  if (!value) return <div className="p-10"><Loading label="Opening the venture" /></div>;
  return (
    <VentureContext.Provider value={value}>
      <TopBar venture={value.venture} theme={theme} />
      <main id="main"><Outlet /></main>
    </VentureContext.Provider>
  );
}

export function VentureIndex() {
  const { ventureId } = useParams();
  const [target, setTarget] = useState<string | null>(null);
  useEffect(() => {
    if (!ventureId) return;
    api.venture(ventureId).then((v) => setTarget(v.plan_version ? "map" : "discuss"), () => setTarget("discuss"));
  }, [ventureId]);
  return target ? <Navigate to={target} replace /> : <div className="p-10"><Loading /></div>;
}
