import { useId, type ReactNode } from "react";

const control = "w-full rounded-md border border-control bg-surface px-3 py-2 text-ink placeholder:text-muted/80 focus-visible:outline-2";

function Wrap({ label, hint, children, id, error }: { label: string; hint?: string; children: ReactNode; id: string; error?: string }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block t-small font-medium">{label}</label>
      {children}
      {hint && !error ? <p className="t-micro text-muted" id={`${id}-hint`}>{hint}</p> : null}
      {error ? <p className="t-micro text-danger" role="alert">{error}</p> : null}
    </div>
  );
}

export function TextField(props: { label: string; value: string; onChange: (v: string) => void; hint?: string; placeholder?: string; type?: string; error?: string; required?: boolean }) {
  const id = useId();
  return (
    <Wrap label={props.label} hint={props.hint} id={id} error={props.error}>
      <input id={id} className={control} type={props.type ?? "text"} value={props.value} placeholder={props.placeholder}
        required={props.required} aria-describedby={props.hint ? `${id}-hint` : undefined} aria-invalid={props.error ? true : undefined}
        onChange={(e) => props.onChange(e.target.value)} />
    </Wrap>
  );
}

export function TextArea(props: { label: string; value: string; onChange: (v: string) => void; hint?: string; placeholder?: string; rows?: number }) {
  const id = useId();
  return (
    <Wrap label={props.label} hint={props.hint} id={id}>
      <textarea id={id} className={control} rows={props.rows ?? 3} value={props.value} placeholder={props.placeholder}
        aria-describedby={props.hint ? `${id}-hint` : undefined} onChange={(e) => props.onChange(e.target.value)} />
    </Wrap>
  );
}

export function SelectField<T extends string>(props: { label: string; value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; hint?: string }) {
  const id = useId();
  return (
    <Wrap label={props.label} hint={props.hint} id={id}>
      <select id={id} className={control} value={props.value} onChange={(e) => props.onChange(e.target.value as T)}>
        {props.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </Wrap>
  );
}

/** Comma-separated list input that stores a string[]. */
export function ListField(props: { label: string; value: string[]; onChange: (v: string[]) => void; hint?: string; placeholder?: string }) {
  return (
    <TextField label={props.label} hint={props.hint ?? "Separate items with commas."} placeholder={props.placeholder}
      value={props.value.join(", ")}
      onChange={(text) => props.onChange(text.split(",").map((s) => s.trimStart()).filter((s, i, all) => s !== "" || i === all.length - 1))} />
  );
}

export function Segmented<T extends string>(props: { label: string; value: T; onChange: (v: T) => void; options: { value: T; label: string }[] }) {
  return (
    <fieldset className="space-y-1.5">
      <legend className="t-small font-medium">{props.label}</legend>
      <div className="inline-flex rounded-md border border-control p-0.5 bg-surface">
        {props.options.map((o) => (
          <label key={o.value} className={`cursor-pointer rounded px-3 py-1.5 t-small ${props.value === o.value ? "bg-accent text-on-accent" : "text-ink hover:bg-sunken"}`}>
            <input type="radio" className="sr-only" checked={props.value === o.value} onChange={() => props.onChange(o.value)} />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
