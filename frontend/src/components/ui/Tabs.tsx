import { useId, type KeyboardEvent, type ReactNode } from "react";

export interface TabItem { id: string; label: ReactNode }

export function Tabs({ items, value, onChange, label }: { items: TabItem[]; value: string; onChange: (id: string) => void; label: string }) {
  const base = useId();
  const onKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    const next = (index + (event.key === "ArrowRight" ? 1 : items.length - 1)) % items.length;
    onChange(items[next].id);
    document.getElementById(`${base}-${items[next].id}`)?.focus();
  };
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 border-b border-line">
      {items.map((item, index) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            id={`${base}-${item.id}`}
            role="tab"
            type="button"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onKeyDown={(e) => onKey(e, index)}
            onClick={() => onChange(item.id)}
            className={`-mb-px border-b-2 px-2.5 py-2 t-small font-medium transition-colors ${selected ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
