import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import { renderWithApp } from "@/test/render";
import { ReviewActions } from "./ReviewActions";

const notice = { value: 90, unit: "days", anchor: "expiration_date", purpose: "non_renewal" };

function setup(onReviewed = vi.fn()) {
  const r = renderWithApp(
    <ReviewActions
      entityType="extracted_item"
      entityId="itm_notice"
      fieldName="notice_period"
      value={notice}
      label="Notice Period"
      onReviewed={onReviewed}
    />,
  );
  return { ...r, onReviewed };
}

const ok = { item: {}, review: {}, renewal: null } as never;

describe("ReviewActions", () => {
  it("approves in one click and confirms with a toast", async () => {
    const review = vi.spyOn(api, "review").mockResolvedValue(ok);
    const { user, onReviewed } = setup();
    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(review).toHaveBeenCalledWith({
      entity_type: "extracted_item",
      entity_id: "itm_notice",
      action: "approve",
      value: undefined,
      note: undefined,
    });
    expect(await screen.findByText("Notice Period approved")).toBeInTheDocument();
    expect(onReviewed).toHaveBeenCalledOnce();
  });

  it("asks for confirmation before rejecting, and Escape cancels", async () => {
    const review = vi.spyOn(api, "review").mockResolvedValue(ok);
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(screen.getByRole("dialog", { name: "Reject extracted information?" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(review).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Reject" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Reject" }));
    expect(review).toHaveBeenCalledWith(expect.objectContaining({ action: "reject" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("sends the corrected value and note when editing", async () => {
    const review = vi.spyOn(api, "review").mockResolvedValue(ok);
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const dialog = screen.getByRole("dialog", { name: "Edit notice period" });
    const length = within(dialog).getByLabelText("Length");
    await user.clear(length);
    await user.type(length, "60");
    await user.type(within(dialog).getByLabelText("Note (optional)"), "Per amendment 2");
    await user.click(within(dialog).getByRole("button", { name: "Save & Approve" }));
    expect(review).toHaveBeenCalledWith(
      expect.objectContaining({ action: "edit", value: { ...notice, value: 60 }, note: "Per amendment 2" }),
    );
  });

  it("keeps the edit dialog open with the validation message when saving fails", async () => {
    vi.spyOn(api, "review").mockRejectedValue(new ApiError("VALIDATION_ERROR", "value.value must be positive", 422));
    const { user, onReviewed } = setup();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Save & Approve" }));
    const dialog = screen.getByRole("dialog");
    expect(await within(dialog).findByText("value.value must be positive")).toBeInTheDocument();
    expect(onReviewed).not.toHaveBeenCalled();
  });

  it("blocks an invalid edit with inline messages and submits once fixed", async () => {
    const review = vi.spyOn(api, "review").mockResolvedValue(ok);
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const dialog = screen.getByRole("dialog", { name: "Edit notice period" });
    // Nothing is flagged on first open.
    expect(within(dialog).queryByText(/whole number|Enter a number/)).not.toBeInTheDocument();

    const length = within(dialog).getByLabelText("Length");
    await user.clear(length);
    expect(within(dialog).getByText("Enter a number")).toBeInTheDocument();
    await user.type(length, "0");
    expect(within(dialog).getByText("Must be a whole number above 0")).toBeInTheDocument();
    expect(length).toHaveAttribute("aria-invalid", "true");
    expect(length).toHaveAccessibleDescription("Must be a whole number above 0");

    await user.click(within(dialog).getByRole("button", { name: "Save & Approve" }));
    expect(review).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.clear(length);
    await user.type(length, "45");
    expect(within(dialog).queryByText("Must be a whole number above 0")).not.toBeInTheDocument();
    expect(length).not.toHaveAttribute("aria-invalid");
    await user.click(within(dialog).getByRole("button", { name: "Save & Approve" }));
    expect(review).toHaveBeenCalledWith(expect.objectContaining({ action: "edit", value: { ...notice, value: 45 } }));
  });

  it("validates obligation edits: description is required", async () => {
    const review = vi.spyOn(api, "review").mockResolvedValue(ok);
    const { user } = renderWithApp(
      <ReviewActions
        entityType="obligation"
        entityId="obl_1"
        value={{ description: "Send usage report", responsible_party: "Acme", frequency: "monthly" }}
        label="Obligation"
        onReviewed={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.clear(screen.getByLabelText("Description"));
    await user.click(screen.getByRole("button", { name: "Save & Approve" }));
    expect(screen.getByText("Enter a description")).toBeInTheDocument();
    expect(review).not.toHaveBeenCalled();
  });

  it("shows an approve failure as an error toast", async () => {
    vi.spyOn(api, "review").mockRejectedValue(new ApiError("NETWORK_ERROR", "Cannot reach the server.", 0));
    const { user, onReviewed } = setup();
    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText("Cannot reach the server.")).toBeInTheDocument();
    expect(onReviewed).not.toHaveBeenCalled();
  });
});
