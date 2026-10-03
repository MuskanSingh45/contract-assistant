import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

/**
 * Catches render errors in one page so the rest of the app (navigation) keeps working.
 * AppShell keys it by route, so navigating away resets it.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ui] page crashed", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Card role="alert" className="flex flex-col items-center px-6 py-12 text-center">
        <h3 className="text-section text-ink">This page failed to display</h3>
        <p className="mt-2 max-w-md text-body text-slate">
          Your data is safe: nothing was changed. Reload to try again. If it keeps happening, the browser console has
          the details.
        </p>
        <p className="mt-3 max-w-md break-words font-mono text-meta text-slate">{this.state.error.message}</p>
        <Button className="mt-5" onClick={() => window.location.reload()}>
          Reload page
        </Button>
      </Card>
    );
  }
}
