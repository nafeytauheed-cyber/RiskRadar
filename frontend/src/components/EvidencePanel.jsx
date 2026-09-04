const FLAG_STYLE = {
  elevated: { text: "text-red-400", bar: "bg-red-500" },
  suppressed: { text: "text-sky-400", bar: "bg-sky-500" },
  normal: { text: "text-slate-500", bar: "bg-slate-600" },
};

export default function EvidencePanel({ evidence, summary, modelDrivers }) {
  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-1">Explainable Evidence</h3>
      <p className="text-sm text-slate-400 mb-5">{summary.narrative}</p>

      <div className="space-y-3 mb-6">
        {evidence.map((e) => {
          const style = FLAG_STYLE[e.flag] || FLAG_STYLE.normal;
          const magnitude = Math.min(100, Math.abs(e.deviation_std) * 12);
          return (
            <div key={e.metric} className="bg-base-850 border border-base-700/50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1.5">
                <div className="text-sm font-medium text-slate-200">{e.metric}</div>
                <div className={`text-xs font-semibold ${style.text}`}>
                  {e.deviation_std > 0 ? "+" : ""}{e.deviation_std}σ
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500 mb-2 mono">
                <span>{e.current_value} {e.unit}</span>
                <span>normal: {e.normal_range[0]}–{e.normal_range[1]} {e.unit}</span>
              </div>
              <div className="h-1.5 rounded-full bg-base-800 overflow-hidden">
                <div className={`h-full ${style.bar} rounded-full`} style={{ width: `${magnitude}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Top Model Drivers</h4>
      <div className="space-y-2">
        {modelDrivers.map((d) => (
          <div key={d.feature} className="flex items-center gap-3 text-xs">
            <div className="w-32 shrink-0 text-slate-400 truncate">{d.feature}</div>
            <div className="flex-1 h-1.5 rounded-full bg-base-800 overflow-hidden">
              <div className="h-full bg-signal-accent rounded-full" style={{ width: `${Math.min(100, d.contribution_pct * 3)}%` }} />
            </div>
            <div className="w-10 text-right text-slate-500 mono">{d.contribution_pct}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
