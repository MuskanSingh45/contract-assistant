import clsx from "clsx";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost" | "link";

const styles: Record<Variant, string> = {
  primary: "bg-indigo text-white hover:bg-indigo-hover disabled:bg-indigo-ring disabled:text-white",
  secondary: "border border-line bg-white text-ink hover:bg-canvas disabled:text-slate/60",
  danger: "border border-line bg-white text-bad hover:bg-bad-soft disabled:text-bad/50",
  ghost: "text-slate hover:bg-canvas hover:text-ink",
  link: "text-indigo hover:underline px-0 h-auto",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  className,
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md"; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-control font-medium transition-colors disabled:cursor-not-allowed",
        variant !== "link" && (size === "sm" ? "h-8 px-3 text-table" : "h-9 px-4 text-body"),
        styles[variant],
        className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
