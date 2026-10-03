import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import { contract } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";
import Contracts from "./Contracts";

describe("Contracts page", () => {
  it("lists contracts with a status that puts conflicts first", async () => {
    vi.spyOn(api, "listContracts").mockResolvedValue([
      contract(),
      contract({
        id: "ctr_globex",
        name: "Globex Hosting Agreement",
        open_clarification_count: 1,
        pending_review_count: 3,
      }),
    ]);
    renderWithApp(<Contracts />);
    const table = await screen.findByRole("table");
    const globex = within(table).getByText("Globex Hosting Agreement").closest("tr")!;
    expect(within(globex).getByText("Potential Conflict")).toBeInTheDocument();
    const acme = within(table).getByText("Acme Services Agreement").closest("tr")!;
    expect(within(acme).getByText("Approved")).toBeInTheDocument();
  });

  it("filters by search text across names and parties", async () => {
    vi.spyOn(api, "listContracts").mockResolvedValue([
      contract(),
      contract({ id: "ctr_globex", name: "Globex Hosting Agreement", parties: ["Initech"] }),
    ]);
    const { user } = renderWithApp(<Contracts />);
    const table = await screen.findByRole("table");
    await user.type(screen.getByPlaceholderText("Search contracts"), "initech");
    expect(within(table).queryByText("Acme Services Agreement")).not.toBeInTheDocument();
    expect(within(table).getByText("Globex Hosting Agreement")).toBeInTheDocument();
  });

  it("shows a retryable error when the backend is down, then recovers", async () => {
    const list = vi
      .spyOn(api, "listContracts")
      .mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Cannot reach the server. Is the backend running?", 0))
      .mockResolvedValueOnce([contract()]);
    const { user } = renderWithApp(<Contracts />);
    expect(await screen.findByText("Cannot reach the server")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(within(await screen.findByRole("table")).getByText("Acme Services Agreement")).toBeInTheDocument();
    expect(list).toHaveBeenCalledTimes(2);
  });
});
