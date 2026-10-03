// Client-side checks for edited values. Mirrors the backend (ai/schemas/*.json value shapes,
// backend/services/review_service.py) so obvious mistakes are caught before a 422.
import type { FieldName } from "@/lib/types";

export type EditErrors = Record<string, string>;
type Value = Record<string, unknown>;

const UNITS = ["days", "months", "years"];
const NOTICE_UNITS = ["days", "business_days", "months"];
const ANCHORS = ["expiration_date", "renewal_date", "other"];
const PURPOSES = ["non_renewal", "termination", "other"];
const RENEWAL_TYPES = ["automatic", "optional", "none"];
const FREQUENCIES = ["one_time", "monthly", "quarterly", "annually", "other"];

const blank = (v: unknown) => v === null || v === undefined || v === "";
const text = (v: unknown) => (typeof v === "string" ? v.trim() : "");

/** A real calendar date in YYYY-MM-DD form. */
export function isIsoDate(v: unknown): boolean {
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const d = new Date(`${v}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === v;
}

function date(v: unknown, required: boolean): string | undefined {
  if (blank(v)) return required ? "Enter a date" : undefined;
  return isIsoDate(v) ? undefined : "Enter a valid date";
}

function positiveInt(v: unknown, required: boolean): string | undefined {
  if (blank(v)) return required ? "Enter a number" : undefined;
  return Number.isInteger(v) && (v as number) >= 1 ? undefined : "Must be a whole number above 0";
}

function oneOf(v: unknown, options: string[], message: string, required = true): string | undefined {
  if (blank(v)) return required ? message : undefined;
  return options.includes(String(v)) ? undefined : message;
}

/** Field key → message for each invalid input. Empty object = valid. */
export function validateEditValue(field: FieldName | "obligation", value: Value): EditErrors {
  const e: Record<string, string | undefined> = {};
  switch (field) {
    case "party":
      e.name = text(value.name) ? undefined : "Enter a name";
      break;
    case "effective_date":
    case "expiration_date":
      e.date = date(value.date, true);
      break;
    case "initial_term":
      e.value = positiveInt(value.value, true);
      e.unit = oneOf(value.unit, UNITS, "Choose a unit");
      break;
    case "renewal_terms":
      e.type = oneOf(value.type, RENEWAL_TYPES, "Choose a renewal type");
      e.period_value = positiveInt(value.period_value, false);
      e.period_unit = oneOf(value.period_unit, UNITS, "Choose a unit", false);
      break;
    case "notice_period":
      e.value = positiveInt(value.value, true);
      e.unit = oneOf(value.unit, NOTICE_UNITS, "Choose a unit");
      e.anchor = oneOf(value.anchor, ANCHORS, "Choose what the notice is before");
      e.purpose = oneOf(value.purpose, PURPOSES, "Choose a purpose");
      break;
    case "termination_clause":
      e.summary = !text(value.summary)
        ? "Enter a summary"
        : String(value.summary).length > 300
          ? "Keep it to 300 characters or fewer"
          : undefined;
      break;
    case "obligation":
      e.description = !text(value.description)
        ? "Enter a description"
        : String(value.description).length > 120
          ? "Keep it to 120 characters or fewer"
          : undefined;
      e.frequency = oneOf(value.frequency, FREQUENCIES, "Choose a frequency", false);
      e.due_date = date(value.due_date, false);
      break;
  }
  return Object.fromEntries(Object.entries(e).filter(([, m]) => m)) as EditErrors;
}
