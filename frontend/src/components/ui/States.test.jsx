import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";
import { Async, ErrorState } from "./States";

describe("ErrorState", () => {
  it("shows a specific title, the message, the reference and a retry", async () => {
    const retry = vi.fn();
    render(
      <ErrorState
        error={new ApiError("INTERNAL_ERROR", "Unexpected server error", 500, null, "req_42")}
        onRetry={retry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong on the server");
    expect(screen.getByText("Unexpected server error")).toBeInTheDocument();
    expect(screen.getByText("Reference: req_42")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("explains an unreachable backend and omits the reference when there is none", () => {
    render(<ErrorState error={new ApiError("NETWORK_ERROR", "Cannot reach the server.", 0)} />);
    expect(screen.getByText("Cannot reach the server")).toBeInTheDocument();
    expect(screen.queryByText(/Reference/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("Async", () => {
  const base = { loading: false, reload: () => {} };

  it("shows the skeleton while loading, then the content", () => {
    const { rerender } = render(
      <Async state={{ ...base, data: undefined, error: undefined, loading: true }} skeleton={<p>loading…</p>}>
        {(d) => <p>{d}</p>}
      </Async>,
    );
    expect(screen.getByText("loading…")).toBeInTheDocument();
    rerender(
      <Async state={{ ...base, data: "loaded", error: undefined }} skeleton={<p>loading…</p>}>
        {(d) => <p>{d}</p>}
      </Async>,
    );
    expect(screen.getByText("loaded")).toBeInTheDocument();
  });

  it("keeps showing stale data when a reload fails", () => {
    render(
      <Async state={{ ...base, data: "stale", error: new ApiError("TIMEOUT", "slow", 0) }}>{(d) => <p>{d}</p>}</Async>,
    );
    expect(screen.getByText("stale")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
