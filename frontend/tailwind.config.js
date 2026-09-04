/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#0a0e14",
          900: "#0f1420",
          850: "#131926",
          800: "#1a2233",
          700: "#243044",
          600: "#334158",
        },
        signal: {
          critical: "#ef4444",
          high: "#f59e0b",
          medium: "#eab308",
          low: "#22c55e",
          accent: "#38bdf8",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(56,189,248,0.15), 0 0 24px rgba(56,189,248,0.08)",
      },
    },
  },
  plugins: [],
};
