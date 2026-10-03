import clsx from "clsx";

export function Card({ className, ...rest }) {
  return <div {...rest} className={clsx("rounded-card border border-line bg-white", className)} />;
}

export function SectionTitle({ children, action, count }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-section text-ink">
        {children}
        {count !== undefined && (
          <span className="rounded-full bg-canvas px-2 text-meta font-semibold text-slate">{count}</span>
        )}
      </h2>
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions, breadcrumb, badge }) {
  return (
    <div className="mb-8">
      {breadcrumb && <div className="mb-3 text-body text-slate">{breadcrumb}</div>}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-page-title text-ink">{title}</h1>
            {badge}
          </div>
          {subtitle && <p className="mt-1 text-body text-slate">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

/** Key/value row used in detail panels. */
export function Field({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-3 last:border-b-0">
      <span className="text-body text-slate">{label}</span>
      <span className="text-right text-body text-ink">{children}</span>
    </div>
  );
}
