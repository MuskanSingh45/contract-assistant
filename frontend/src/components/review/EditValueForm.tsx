import { useId, useState, type ReactNode } from "react";
import type { FieldName } from "@/lib/types";
import { validateEditValue } from "./validation";

type Value = Record<string, unknown>;

const input =
  "h-9 w-full rounded-control border border-line px-3 text-body focus:border-indigo focus:ring-2 focus:ring-indigo-ring aria-[invalid=true]:border-bad";

/** Accessibility + touch props a Row hands to its input. */
type Ctl = { "aria-invalid"?: boolean; "aria-describedby"?: string; onBlur: () => void };

function Row({
  label,
  error,
  onTouch,
  children,
}: {
  label: string;
  error?: string;
  onTouch: () => void;
  children: (ctl: Ctl) => ReactNode;
}) {
  const id = useId();
  return (
    <div>
      <label className="block">
        <span className="mb-1 block text-table text-slate">{label}</span>
        {children({
          "aria-invalid": error ? true : undefined,
          "aria-describedby": error ? id : undefined,
          onBlur: onTouch,
        })}
      </label>
      {error && (
        <p id={id} className="mt-1 text-table text-bad">
          {error}
        </p>
      )}
    </div>
  );
}

function Sel({
  value,
  options,
  onChange,
  ctl,
}: {
  value: unknown;
  options: [string, string][];
  onChange: (v: string) => void;
  ctl: Ctl;
}) {
  const v = String(value ?? "");
  // A value not among the options (e.g. a blank answer) shows a placeholder instead of silently showing option 1.
  const opts: [string, string][] = options.some(([o]) => o === v) ? options : [["", "Select…"], ...options];
  return (
    <select className={input} value={v} onChange={(e) => onChange(e.target.value)} {...ctl}>
      {opts.map(([o, l]) => (
        <option key={o} value={o}>
          {l}
        </option>
      ))}
    </select>
  );
}

const units: [string, string][] = [
  ["days", "days"],
  ["months", "months"],
  ["years", "years"],
];

/** Field-aware editor. `field` is an extracted item field_name, or "obligation". */
export function EditValueForm({
  field,
  value,
  onChange,
  showErrors = false,
}: {
  field: FieldName | "obligation";
  value: Value;
  onChange: (v: Value) => void;
  /** reveal every validation message (set after a save attempt); otherwise only touched fields show theirs */
  showErrors?: boolean;
}) {
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const errors = validateEditValue(field, value);
  const touch = (k: string) => setTouched((t) => (t.has(k) ? t : new Set(t).add(k)));
  /** Row props for value key `k`. */
  const at = (k: string) => ({
    error: showErrors || touched.has(k) ? errors[k] : undefined,
    onTouch: () => touch(k),
  });
  const set = (k: string, v: unknown) => {
    touch(k);
    onChange({ ...value, [k]: v });
  };
  const num = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    set(k, e.target.value === "" ? null : Number(e.target.value));

  switch (field) {
    case "party":
      return (
        <div className="grid gap-3">
          <Row label="Name" {...at("name")}>
            {(ctl) => (
              <input
                className={input}
                value={String(value.name ?? "")}
                onChange={(e) => set("name", e.target.value)}
                {...ctl}
              />
            )}
          </Row>
          <Row label="Role" {...at("role")}>
            {(ctl) => (
              <input
                className={input}
                value={String(value.role ?? "")}
                onChange={(e) => set("role", e.target.value || null)}
                {...ctl}
              />
            )}
          </Row>
        </div>
      );
    case "effective_date":
    case "expiration_date":
      return (
        <Row label="Date" {...at("date")}>
          {(ctl) => (
            <input
              type="date"
              className={input}
              value={String(value.date ?? "")}
              onChange={(e) => {
                touch("date");
                onChange({ date: e.target.value, date_text: e.target.value });
              }}
              {...ctl}
            />
          )}
        </Row>
      );
    case "initial_term":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Row label="Length" {...at("value")}>
            {(ctl) => (
              <input
                type="number"
                min={1}
                className={input}
                value={String(value.value ?? "")}
                onChange={num("value")}
                {...ctl}
              />
            )}
          </Row>
          <Row label="Unit" {...at("unit")}>
            {(ctl) => <Sel ctl={ctl} value={value.unit} options={units} onChange={(v) => set("unit", v)} />}
          </Row>
        </div>
      );
    case "renewal_terms":
      return (
        <div className="grid grid-cols-3 gap-3">
          <Row label="Type" {...at("type")}>
            {(ctl) => (
              <Sel
                ctl={ctl}
                value={value.type}
                options={[
                  ["automatic", "Automatic"],
                  ["optional", "Optional"],
                  ["none", "None"],
                ]}
                onChange={(v) => set("type", v)}
              />
            )}
          </Row>
          <Row label="Period" {...at("period_value")}>
            {(ctl) => (
              <input
                type="number"
                min={1}
                className={input}
                value={String(value.period_value ?? "")}
                onChange={num("period_value")}
                {...ctl}
              />
            )}
          </Row>
          <Row label="Unit" {...at("period_unit")}>
            {(ctl) => (
              <Sel ctl={ctl} value={value.period_unit} options={units} onChange={(v) => set("period_unit", v)} />
            )}
          </Row>
        </div>
      );
    case "notice_period":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Row label="Length" {...at("value")}>
            {(ctl) => (
              <input
                type="number"
                min={1}
                className={input}
                value={String(value.value ?? "")}
                onChange={num("value")}
                {...ctl}
              />
            )}
          </Row>
          <Row label="Unit" {...at("unit")}>
            {(ctl) => (
              <Sel
                ctl={ctl}
                value={value.unit}
                options={[
                  ["days", "days"],
                  ["business_days", "business days"],
                  ["months", "months"],
                ]}
                onChange={(v) => set("unit", v)}
              />
            )}
          </Row>
          <Row label="Before" {...at("anchor")}>
            {(ctl) => (
              <Sel
                ctl={ctl}
                value={value.anchor}
                options={[
                  ["expiration_date", "expiration"],
                  ["renewal_date", "renewal"],
                  ["other", "other event"],
                ]}
                onChange={(v) => set("anchor", v)}
              />
            )}
          </Row>
          <Row label="Purpose" {...at("purpose")}>
            {(ctl) => (
              <Sel
                ctl={ctl}
                value={value.purpose}
                options={[
                  ["non_renewal", "Non-renewal"],
                  ["termination", "Termination"],
                  ["other", "Other"],
                ]}
                onChange={(v) => set("purpose", v)}
              />
            )}
          </Row>
        </div>
      );
    case "termination_clause":
      return (
        <Row label="Summary" {...at("summary")}>
          {(ctl) => (
            <textarea
              rows={3}
              className={`${input} h-auto py-2`}
              value={String(value.summary ?? "")}
              onChange={(e) => set("summary", e.target.value)}
              {...ctl}
            />
          )}
        </Row>
      );
    case "obligation":
      return (
        <div className="grid gap-3">
          <Row label="Description" {...at("description")}>
            {(ctl) => (
              <input
                className={input}
                value={String(value.description ?? "")}
                onChange={(e) => set("description", e.target.value)}
                {...ctl}
              />
            )}
          </Row>
          <div className="grid grid-cols-2 gap-3">
            <Row label="Responsible party" {...at("responsible_party")}>
              {(ctl) => (
                <input
                  className={input}
                  value={String(value.responsible_party ?? "")}
                  onChange={(e) => set("responsible_party", e.target.value || null)}
                  {...ctl}
                />
              )}
            </Row>
            <Row label="Frequency" {...at("frequency")}>
              {(ctl) => (
                <Sel
                  ctl={ctl}
                  value={value.frequency ?? ""}
                  onChange={(v) => set("frequency", v || null)}
                  options={[
                    ["", "Not stated"],
                    ["one_time", "One time"],
                    ["monthly", "Monthly"],
                    ["quarterly", "Quarterly"],
                    ["annually", "Annually"],
                    ["other", "Other"],
                  ]}
                />
              )}
            </Row>
          </div>
          <Row label="Due date (sets an explicit date)" {...at("due_date")}>
            {(ctl) => (
              <input
                type="date"
                className={input}
                value={String(value.due_date ?? "")}
                onChange={(e) => set("due_date", e.target.value || null)}
                {...ctl}
              />
            )}
          </Row>
        </div>
      );
  }
}

/** The value object to send for an obligation edit (only editable keys, only changed ones). */
export function obligationEditValue(original: Value, edited: Value): Value {
  const keys = ["description", "responsible_party", "frequency", "due_date"];
  const out: Value = {};
  for (const k of keys) if (edited[k] !== original[k] && !(k === "due_date" && !edited[k])) out[k] = edited[k];
  return out;
}
