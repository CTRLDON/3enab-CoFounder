import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Theme } from "../types/api";

const root = () => document.documentElement;

export function applyTheme(tokens: Record<string, string> | null): void {
  const style = root().style;
  for (let i = style.length - 1; i >= 0; i--) {
    const prop = style[i];
    if (prop.startsWith("--c-")) style.removeProperty(prop);
  }
  if (!tokens) return;
  for (const [key, value] of Object.entries(tokens)) style.setProperty(`--c-${key}`, value);
}

/**
 * Fetches the venture's adaptive palette from the backend and applies it as CSS variables.
 * `refreshKey` should change whenever the plan or state changes (e.g. `${state}:${planVersion}`).
 */
export function useVentureTheme(ventureId: string | undefined, refreshKey: string) {
  const [theme, setTheme] = useState<Theme | null>(null);
  useEffect(() => {
    if (!ventureId) return;
    let cancelled = false;
    api.theme(ventureId).then(
      (t) => {
        if (cancelled) return;
        setTheme(t);
        applyTheme(t.tokens);
      },
      () => undefined, // keep the current palette if the theme cannot load
    );
    return () => {
      cancelled = true;
    };
  }, [ventureId, refreshKey]);
  useEffect(() => () => applyTheme(null), []);
  return theme;
}
