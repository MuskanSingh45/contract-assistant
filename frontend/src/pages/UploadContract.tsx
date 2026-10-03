import { useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Upload, CheckCircle2 } from "lucide-react";
import { api, ApiError, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PageHeader, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
export default function UploadContract() {
  const [params] = useSearchParams();
  const id = params.get("contract");
  const contract = useApi(() => (id ? api.getContract(id) : Promise.resolve(undefined)), [id]);
  const [file, setFile] = useState<File>(),
    [name, setName] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null),
    nav = useNavigate(),
    toast = useToast();
  function choose(f?: File) {
    if (!f) return;
    if (!/\.(pdf|docx)$/i.test(f.name)) {
      setError("Choose a PDF or DOCX file.");
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setError("File exceeds the 20 MB limit.");
      return;
    }
    setError("");
    setFile(f);
  }
  async function submit() {
    if (!file) return;
    setBusy(true);
    setError("");
    let cid = id;
    try {
      if (id) await api.uploadVersion(id, file);
      else {
        const out = await api.uploadContract(file, name || undefined);
        cid = out.contract.id;
      }
      try {
        await api.analyze(cid!);
        nav(`/contracts/${cid}/analyzing`);
      } catch (e) {
        if (e instanceof ApiError && e.code === "AI_UNAVAILABLE") {
          toast("Uploaded, but the AI model is unavailable. Start Ollama and re-analyze.", "error");
          nav(`/contracts/${cid}`);
          return;
        }
        throw e;
      }
    } catch (e) {
      const m = errorMessage(e);
      setError(m);
      toast(m, "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        breadcrumb={
          <>
            <Link to="/contracts" className="hover:text-ink">
              Contracts
            </Link>{" "}
            / <span className="text-ink">{id ? "Upload New Version" : "Upload Contract"}</span>
          </>
        }
        title={id ? "Upload New Version" : "Upload Contract"}
        subtitle={
          id && contract.data
            ? contract.data.name
            : "Upload a contract to extract key dates, obligations, and renewal information."
        }
      />
      <div className="mx-auto max-w-4xl">
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            choose(e.dataTransfer.files[0]);
          }}
          className="flex min-h-72 w-full flex-col items-center justify-center rounded-card border-2 border-dashed border-line bg-canvas/40 p-8 text-center hover:border-indigo"
        >
          <span className="mb-4 rounded-card border border-line bg-white p-4 text-indigo">
            <Upload />
          </span>
          <b>Upload contract</b>
          <span className="mt-3 text-body text-slate">
            Drag and drop your file here, or <span className="text-indigo">Browse files</span>
          </span>
          <small className="mt-2 text-slate">PDF or DOCX · up to 20 MB</small>
          <input
            ref={input}
            type="file"
            accept=".pdf,.docx,application/pdf"
            className="hidden"
            onChange={(e) => choose(e.target.files?.[0])}
          />
        </button>
        {file && (
          <Card className="mt-4 flex items-center gap-4 p-4">
            <span className="rounded-control bg-indigo-soft p-3 text-table font-semibold text-indigo">
              {file.name.toLowerCase().endsWith(".pdf") ? "PDF" : "DOCX"}
            </span>
            <span className="flex-1">
              <b>{file.name}</b>
              <small className="block text-slate">
                {file.size < 1024 * 1024
                  ? `${Math.max(1, Math.round(file.size / 1024))} KB`
                  : `${(file.size / 1024 / 1024).toFixed(1)} MB`}{" "}
                · Ready to analyze
              </small>
            </span>
            <CheckCircle2 className="text-ok" />
            <Button onClick={() => setFile(undefined)}>Remove</Button>
          </Card>
        )}
        {!id && (
          <label className="mt-5 block text-body">
            Contract name (optional)
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-2 block h-10 w-full rounded-control border border-line px-3"
            />
          </label>
        )}
        {error && <p className="mt-4 rounded-control bg-bad-soft p-3 text-body text-bad">{error}</p>}
        <div className="mt-8 flex justify-end gap-3 border-t border-line pt-6">
          <Button onClick={() => nav("/contracts")}>Cancel</Button>
          <Button variant="primary" disabled={!file} loading={busy} onClick={submit}>
            Analyze Contract
          </Button>
        </div>
      </div>
    </>
  );
}
