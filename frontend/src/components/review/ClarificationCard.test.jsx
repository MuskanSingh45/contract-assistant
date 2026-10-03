import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import { conflict } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";
import { ClarificationCard } from "./ClarificationCard";

describe("ClarificationCard (conflict)", () => {
  it("shows both cited values and never pre-selects one", () => {
    renderWithApp(<ClarificationCard clarification={conflict()} onResolved={() => {}} />);
    expect(screen.getByText("Which notice period applies: 90 days or 60 days?")).toBeInTheDocument();
    expect(screen.getByText("90 days before expiration")).toBeInTheDocument();
    expect(screen.getByText("60 days before expiration")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Use this value" })).toHaveLength(2);
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument();
  });

  it("resolves with the chosen source and a note, then reports the recalculated renewal", async () => {
    const renewal = { contract_id: "ctr_globex", notice_deadline: "2026-11-01" };
    const resolve = vi
      .spyOn(api, "resolveClarification")
      .mockResolvedValue({ clarification: conflict({ status: "resolved" }), renewal });
    const onResolved = vi.fn();
    const { user } = renderWithApp(<ClarificationCard clarification={conflict()} onResolved={onResolved} />);

    await user.type(screen.getByPlaceholderText(/Confirmed with legal/), "Amendment wins");
    await user.click(screen.getAllByRole("button", { name: "Use this value" })[1]);

    expect(resolve).toHaveBeenCalledWith("clr_1", { action: "select", entity_id: "itm_60", note: "Amendment wins" });
    await waitFor(() => expect(onResolved).toHaveBeenCalledWith(renewal));
    expect(await screen.findByText("Answer saved · deadlines recalculated")).toBeInTheDocument();
  });

  it("shows the server's message inline when resolving fails, and stays open", async () => {
    vi.spyOn(api, "resolveClarification").mockRejectedValue(
      new ApiError("CLARIFICATION_ALREADY_CLOSED", "This question was already answered.", 409),
    );
    const onResolved = vi.fn();
    const { user } = renderWithApp(<ClarificationCard clarification={conflict()} onResolved={onResolved} />);
    await user.click(screen.getByRole("button", { name: "Mark as reviewed" }));
    expect(await screen.findByText("This question was already answered.")).toBeInTheDocument();
    expect(onResolved).not.toHaveBeenCalled();
    expect(screen.getAllByRole("button", { name: "Use this value" })).toHaveLength(2);
  });

  it("shows a resolved clarification read-only with the selected source", () => {
    const resolved = conflict({
      status: "resolved",
      resolved_at: "2026-10-03T10:00:00Z",
      resolution_note: "Per legal",
    });
    resolved.options[0].review_status = "approved";
    renderWithApp(<ClarificationCard clarification={resolved} onResolved={() => {}} />);
    expect(screen.getByText("Resolved")).toBeInTheDocument();
    expect(screen.getByText(/Source 1 · selected/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use this value" })).not.toBeInTheDocument();
    expect(screen.getByText(/Per legal/)).toBeInTheDocument();
  });
});

describe("ClarificationCard (missing information)", () => {
  const missing = () =>
    conflict({
      kind: "missing",
      field_name: "expiration_date",
      question: "What is the expiration date?",
      options: [],
    });

  it("reveals errors on save, does not call the API while invalid, and submits once fixed", async () => {
    const resolve = vi
      .spyOn(api, "resolveClarification")
      .mockResolvedValue({ clarification: missing(), renewal: null });
    const { user } = renderWithApp(<ClarificationCard clarification={missing()} onResolved={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Answer question" }));
    expect(screen.queryByText("Enter a date")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save answer" }));
    expect(screen.getByText("Enter a date")).toBeInTheDocument();
    expect(screen.getByLabelText("Date")).toHaveAttribute("aria-invalid", "true");
    expect(resolve).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Date"), "2027-06-30");
    expect(screen.queryByText("Enter a date")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save answer" }));
    expect(resolve).toHaveBeenCalledWith("clr_1", {
      action: "custom",
      value: { date: "2027-06-30", date_text: "2027-06-30" },
      note: undefined,
    });
  });

  it("blocks a notice period of 0 in a custom answer", async () => {
    const resolve = vi.spyOn(api, "resolveClarification");
    const { user } = renderWithApp(<ClarificationCard clarification={conflict()} onResolved={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Enter a different value" }));
    const length = screen.getByLabelText("Length");
    await user.clear(length);
    await user.type(length, "0");
    expect(screen.getByText("Must be a whole number above 0")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save answer" }));
    expect(resolve).not.toHaveBeenCalled();
  });
});
