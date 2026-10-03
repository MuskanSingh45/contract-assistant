/** Design tokens from the Contract Assistant design system (page 1 of the product UI). */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        ink: "#0F172A",
        slate: { DEFAULT: "#64748B" },
        line: "#E5E7EB",
        canvas: "#F8F9FB",
        indigo: { DEFAULT: "#4F46E5", hover: "#4338CA", soft: "#EEF2FF", ring: "#C7D2FE" },
        ok: { DEFAULT: "#067647", soft: "#ECFDF3" },
        warn: { DEFAULT: "#B54708", soft: "#FFFAEB" },
        bad: { DEFAULT: "#B42318", soft: "#FEF3F2" },
      },
      borderRadius: { control: "6px", card: "8px" },
      fontSize: {
        "page-title": ["24px", { lineHeight: "32px", fontWeight: "600" }],
        section: ["15px", { lineHeight: "22px", fontWeight: "600" }],
        value: ["17px", { lineHeight: "24px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "20px" }],
        table: ["13px", { lineHeight: "20px" }],
        meta: ["12px", { lineHeight: "16px" }],
        label: ["11px", { lineHeight: "16px", fontWeight: "600", letterSpacing: "0.04em" }],
      },
    },
  },
  plugins: [],
};
