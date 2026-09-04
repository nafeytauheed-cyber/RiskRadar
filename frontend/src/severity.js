export const SEVERITY_COLORS = {
  Critical: { text: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/40", dot: "bg-red-500", hex: "#ef4444" },
  High: { text: "text-amber-400", bg: "bg-amber-500/15", border: "border-amber-500/40", dot: "bg-amber-500", hex: "#f59e0b" },
  Medium: { text: "text-yellow-300", bg: "bg-yellow-400/10", border: "border-yellow-400/30", dot: "bg-yellow-400", hex: "#eab308" },
  Low: { text: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/40", dot: "bg-emerald-500", hex: "#22c55e" },
};

export function severityStyle(severity) {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.Low;
}
