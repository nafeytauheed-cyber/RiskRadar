export default function SimilarIncidents({ incidents }) {
  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-1">Historical Failure Similarity</h3>
      <p className="text-xs text-slate-500 mb-4">Nearest matches from past run-to-failure incidents</p>
      {incidents.length === 0 && <div className="text-sm text-slate-500">No comparable historical incidents found.</div>}
      <div className="space-y-3">
        {incidents.map((inc) => (
          <div key={inc.incident_id} className="bg-base-850 border border-base-700/50 rounded-lg p-3.5">
            <div className="flex items-center justify-between mb-1">
              <div className="text-sm font-medium text-slate-200 mono">{inc.incident_id}</div>
              <div className="text-sm font-bold text-signal-accent">{inc.similarity_pct}%</div>
            </div>
            <div className="text-xs text-slate-400 mb-2">
              {inc.equipment_type} · root cause: {inc.root_cause.replaceAll("_", " ")} · {inc.failure_date}
            </div>
            <div className="text-xs text-slate-500">Resolved by: {inc.action_taken}</div>
            <div className="mt-2 h-1 rounded-full bg-base-800 overflow-hidden">
              <div className="h-full bg-signal-accent rounded-full" style={{ width: `${inc.similarity_pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
