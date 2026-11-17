import { Palette } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Theme } from "../../types/api";

export function PaletteChip({ theme }: { theme: Theme | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  if (!theme) return null;
  const passed = theme.contrast.filter((c) => c.passes).length;
  return (
    <div className="relative" ref={ref}>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="inline-flex h-8 items-center gap-1.5 rounded-md px-2 t-small text-muted hover:bg-sunken hover:text-ink">
        <span className="size-3 rounded-full" style={{ background: "var(--c-accent)" }} aria-hidden />
        <Palette className="size-4" aria-hidden />
        <span className="hidden lg:inline">{theme.label}</span>
      </button>
      {open ? (
        <div role="dialog" aria-label="About this palette"
          className="absolute right-0 top-10 z-50 w-80 rounded-lg border border-line bg-surface p-4 shadow-[0_8px_30px_-12px_rgba(0,0,0,.25)] fade-in">
          <p className="t-small font-semibold">Palette follows the plan</p>
          <p className="t-small mt-1">{theme.label}</p>
          <p className="t-small text-muted mt-2">{theme.rationale}</p>
          {theme.matched_terms.length ? (
            <p className="t-micro text-muted mt-2">Matched in {theme.source}: {theme.matched_terms.join(", ")}</p>
          ) : <p className="t-micro text-muted mt-2">Based on {theme.source}.</p>}
          {theme.state_note ? <p className="t-micro mt-2">{theme.state_note}</p> : null}
          <p className="t-micro mt-3 text-muted">
            WCAG contrast: {passed} of {theme.contrast.length} checks pass{theme.all_contrast_checks_pass ? "" : " — some colours need review"}.
          </p>
        </div>
      ) : null}
    </div>
  );
}
