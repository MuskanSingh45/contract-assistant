// Render a component with the app's providers, on a route, like main.jsx does.
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { SourceProvider } from "@/components/SourceDrawer";
import { ToastProvider } from "@/components/ui/Toast";

/** Shows the current URL so tests can assert on navigation. */
function LocationProbe() {
  const { pathname, search } = useLocation();
  return <div data-testid="location">{pathname + search}</div>;
}

export function renderWithApp(ui, { route = "/", path = "*" } = {}) {
  const user = userEvent.setup();
  const result = render(
    <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <SourceProvider>
          <Routes>
            <Route path={path} element={ui} />
            <Route path="*" element={null} />
          </Routes>
          <LocationProbe />
        </SourceProvider>
      </ToastProvider>
    </MemoryRouter>,
  );
  return { user, ...result };
}

/** A fetch Response with a JSON body, as the backend sends it. */
export function jsonResponse(body, status = 200, headers = {}) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}
