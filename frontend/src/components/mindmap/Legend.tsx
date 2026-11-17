import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { EconomicClass } from "../../types/api";
import { ECONOMIC_META } from "../ui/Badges";

const ORDER: EconomicClass[] = ["revenue", "expense", "mixed", "strategic", "unknown"];

export function Legend({ defaultOpen = true }: { defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-line bg-surface/95 p-2.5 backdrop-blur">
      <button type="button" className="flex w-full items-center justify-between gap-6 t-micro font-semibold" aria-expanded={open} onClick={() => setOpen(!open)}>
        Economic role <ChevronDown className={`size-3.5 transition-transform ${open ? "" : "-rotate-90"}`} aria-hidden />
      </button>
      {open ? (
        <ul className="mt-2 space-y-1.5">
          {ORDER.map((key) => {
            const meta = ECONOMIC_META[key];
            return (
              <li key={key} className="flex items-center gap-2 t-micro">
                <span className={`econ-stripe econ-${key} h-4`} aria-hidden />
                <meta.Icon className="size-3.5" style={{ color: `var(--c-econ-${key}-text)` }} aria-hidden />
                <span>{meta.label}</span>
              </li>
            );
          })}
          <li className="pt-1 t-micro text-muted max-w-[200px]">Revenue marks potential income, not profit.</li>
        </ul>
      ) : null}
    </div>
  );
}
