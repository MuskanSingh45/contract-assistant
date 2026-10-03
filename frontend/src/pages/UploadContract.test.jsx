import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import { renderWithApp } from "@/test/render";
import UploadContract from "./UploadContract";

const pdf = () => new File(["%PDF-1.7"], "acme.pdf", { type: "application/pdf" });

function choose(container, file) {
  const input = container.querySelector('input[type="file"]');
  fireEvent.change(input, { target: { files: [file] } });
}

function setup() {
  return renderWithApp(<UploadContract />, { route: "/contracts/upload", path: "/contracts/upload" });
}

describe("UploadContract", () => {
  it("rejects unsupported file types before uploading", () => {
    const upload = vi.spyOn(api, "uploadContract");
    const { container } = setup();
    choose(container, new File(["hi"], "notes.txt", { type: "text/plain" }));
    expect(screen.getByText("Choose a PDF or DOCX file.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze Contract" })).toBeDisabled();
    expect(upload).not.toHaveBeenCalled();
  });

  it("rejects files over the 20 MB limit", () => {
    const { container } = setup();
    const big = new File(["x"], "big.pdf", { type: "application/pdf" });
    Object.defineProperty(big, "size", { value: 21 * 1024 * 1024 });
    choose(container, big);
    expect(screen.getByText("File exceeds the 20 MB limit.")).toBeInTheDocument();
  });

  it("uploads, starts analysis and opens the progress page", async () => {
    vi.spyOn(api, "uploadContract").mockResolvedValue({
      contract: { id: "ctr_new" },
      version: { id: "ver_1" },
    });
    const analyze = vi.spyOn(api, "analyze").mockResolvedValue({});
    const { container, user } = setup();
    choose(container, pdf());
    await user.type(screen.getByLabelText(/Contract name/), "Acme MSA");
    await user.click(screen.getByRole("button", { name: "Analyze Contract" }));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/contracts/ctr_new/analyzing"));
    expect(api.uploadContract).toHaveBeenCalledWith(expect.any(File), "Acme MSA");
    expect(analyze).toHaveBeenCalledWith("ctr_new");
  });

  it("keeps the upload and explains when the AI model is unavailable", async () => {
    vi.spyOn(api, "uploadContract").mockResolvedValue({
      contract: { id: "ctr_new" },
      version: { id: "ver_1" },
    });
    vi.spyOn(api, "analyze").mockRejectedValue(new ApiError("AI_UNAVAILABLE", "Ollama is not reachable.", 503));
    const { container, user } = setup();
    choose(container, pdf());
    await user.click(screen.getByRole("button", { name: "Analyze Contract" }));
    expect(await screen.findByText(/AI model is unavailable/)).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/contracts/ctr_new");
  });

  it("shows the server's reason when the upload is refused", async () => {
    vi.spyOn(api, "uploadContract").mockRejectedValue(
      new ApiError("INVALID_DOCUMENT", "Unsupported document format. Upload a PDF or DOCX file.", 415),
    );
    const { container, user } = setup();
    choose(container, pdf());
    await user.click(screen.getByRole("button", { name: "Analyze Contract" }));
    expect(await screen.findAllByText("Unsupported document format. Upload a PDF or DOCX file.")).not.toHaveLength(0);
    expect(screen.getByTestId("location")).toHaveTextContent("/contracts/upload");
  });
});
