import clsx from "clsx";
import { CalendarClock, CheckSquare, FileText, HelpCircle, Inbox, LayoutDashboard, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "@/lib/api";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CountPill } from "@/components/ui/Badge";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/contracts", label: "Contracts", icon: FileText },
  { to: "/obligations", label: "Obligations", icon: CheckSquare },
  { to: "/renewals", label: "Renewals", icon: CalendarClock },
  { to: "/review", label: "Review Queue", icon: Inbox, badge: true },
];

function useReviewCount() {
  const [count, setCount] = useState(0);
  const location = useLocation();
  useEffect(() => {
    Promise.all([api.reviewQueue(), api.clarifications({ status: "open" })])
      .then(([q, c]) => setCount(q.length + c.length))
      .catch(() => {}); // badge only: the page itself shows connection errors
  }, [location.pathname]);
  return count;
}

function Item({ to, label, icon: Icon, badge }: Omit<(typeof nav)[number], "badge"> & { badge?: number }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          "flex items-center gap-3 rounded-card px-3 py-2.5 text-body",
          isActive ? "bg-indigo-soft font-medium text-indigo" : "text-ink hover:bg-white",
        )
      }
    >
      <Icon className="h-4 w-4" />
      <span className="flex-1">{label}</span>
      {typeof badge === "number" && badge > 0 && <CountPill n={badge} tone="warn" />}
    </NavLink>
  );
}

export function AppShell() {
  const reviewCount = useReviewCount();
  const { pathname } = useLocation();
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-line bg-canvas px-3 py-5">
        <div className="mb-8 flex items-center gap-2 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-control bg-indigo text-meta font-semibold text-white">
            C
          </div>
          <span className="text-body font-semibold text-ink">Contract Assistant</span>
        </div>
        <nav className="flex flex-col gap-1">
          {nav.map((n) => (
            <Item key={n.to} {...n} badge={n.badge ? reviewCount : undefined} />
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-1">
          <Item to="/settings" label="Settings" icon={Settings} />
          <Item to="/help" label="Help / About" icon={HelpCircle} />
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-10 py-10">
        <div className="mx-auto max-w-6xl">
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
