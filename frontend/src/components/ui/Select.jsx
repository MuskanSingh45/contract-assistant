import { ChevronDown } from "lucide-react";

/** Filter dropdown styled like the design's "Status: All ▾" controls. */
export function FilterSelect({ label, value, options, onChange }) {
  return (
    <label className="relative inline-flex h-10 items-center rounded-control border border-line bg-white pl-4 pr-9 text-body text-ink hover:bg-canvas">
      <span className="pointer-events-none">
        {label}: {options.find((o) => o.value === value)?.label}
      </span>
      <ChevronDown className="pointer-events-none absolute right-3 h-4 w-4 text-slate" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="absolute inset-0 cursor-pointer opacity-0"
        aria-label={label}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SearchInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="h-10 w-full max-w-md rounded-control border border-line px-4 text-body placeholder:text-slate focus:border-indigo focus:ring-2 focus:ring-indigo-ring"
    />
  );
}
