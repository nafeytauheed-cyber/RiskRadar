const PRIORITY_STYLE = {
  Immediate: "border-red-500/40 text-red-400 bg-red-500/10",
  "Short-term": "border-amber-500/40 text-amber-400 bg-amber-500/10",
  "Ongoing Monitoring": "border-sky-500/40 text-sky-400 bg-sky-500/10",
};

export default function RecommendedActions({ actions, onGenerateReport }) {
  const groups = [
    { key: "immediate", label: "Immediate" },
    { key: "short_term", label: "Short-term" },
    { key: "monitoring", label: "Ongoing Monitoring" },
  ];

  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Recommended Action</h3>
        <div className="text-xs font-semibold text-amber-400 mono">{actions.urgency}</div>
      </div>

      <div className="space-y-4 mt-4">
        {groups.map((g) => {
          const items = actions[g.key];
          if (!items || items.length === 0) return null;
          return (
            <div key={g.key}>
              <div className={`inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border mb-2 ${PRIORITY_STYLE[g.label]}`}>
                {g.label}
              </div>
              <ul className="space-y-1.5">
                {items.map((item, i) => (
                  <li key={i} className="text-sm text-slate-300 flex gap-2">
                    <span className="text-slate-600 mt-0.5">—</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      <button
        onClick={onGenerateReport}
        className="no-print mt-6 w-full py-2.5 rounded-lg bg-signal-accent/15 border border-signal-accent/40 text-signal-accent text-sm font-semibold hover:bg-signal-accent/25 transition-colors"
      >
        Generate Investigation Report
      </button>
    </div>
  );
}
