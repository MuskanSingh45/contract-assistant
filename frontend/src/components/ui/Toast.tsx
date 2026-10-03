import { AlertCircle, Check } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Tone = "success" | "info" | "error";
interface Toast {
  id: number;
  tone: Tone;
  text: string;
}

const Ctx = createContext<(text: string, tone?: Tone) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Tone = "success") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, tone, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex w-96 flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={
              t.tone === "error"
                ? "flex items-center gap-3 rounded-card border border-line bg-white px-4 py-3 text-body text-ink shadow-lg"
                : "flex items-center gap-3 rounded-card bg-ink px-4 py-3 text-body text-white shadow-lg"
            }
          >
            {t.tone === "error" ? (
              <AlertCircle className="h-4 w-4 shrink-0 text-bad" />
            ) : t.tone === "info" ? (
              <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-amber-400" />
            ) : (
              <Check className="h-4 w-4 shrink-0 text-emerald-400" />
            )}
            {t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

/** toast("Renewal Period approved") · toast("Upload failed", "error") */
export function useToast() {
  return useContext(Ctx);
}
