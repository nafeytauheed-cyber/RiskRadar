export default function Timeline({ events }) {
  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-5">Failure / Event Timeline</h3>
      {events.length === 0 && <div className="text-sm text-slate-500">No recorded events.</div>}
      <div className="relative pl-6 max-h-[420px] overflow-y-auto pr-2">
        <div className="absolute left-[7px] top-1 bottom-1 w-px bg-base-700" />
        {events.map((ev, i) => (
          <div key={i} className="relative mb-5 last:mb-0">
            <div
              className={`absolute -left-6 top-0.5 w-3.5 h-3.5 rounded-full border-2 ${
                ev.type === "maintenance"
                  ? "bg-base-900 border-signal-accent"
                  : "bg-base-900 border-amber-500"
              }`}
            />
            <div className="text-[11px] mono text-slate-500 mb-0.5">
              {ev.date}{ev.end_date !== ev.date ? ` → ${ev.end_date}` : ""}
            </div>
            <div className="text-sm text-slate-200">{ev.label}</div>
            {ev.type === "anomaly_cluster" && (
              <div className="text-xs text-slate-500 mt-0.5">Avg anomaly score: {ev.avg_anomaly_score}/100</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
