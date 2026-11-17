import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const styles: Record<Variant, string> = {
  primary: "bg-accent text-on-accent hover:bg-accent-hover border border-transparent",
  secondary: "bg-surface text-ink border border-control hover:bg-sunken",
  ghost: "bg-transparent text-ink border border-transparent hover:bg-sunken",
  danger: "bg-surface text-danger border border-control hover:bg-sunken",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  busy?: boolean;
  icon?: ReactNode;
}

export function Button({ variant = "secondary", size = "md", busy = false, icon, children, className = "", disabled, ...rest }: Props) {
  const sizing = size === "sm" ? "h-8 px-2.5 text-[0.867rem] gap-1.5" : "h-10 px-3.5 gap-2";
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${sizing} ${styles[variant]} ${className}`}
    >
      {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}
