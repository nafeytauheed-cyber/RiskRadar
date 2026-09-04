import { useNavigate } from "react-router-dom";
import { severityStyle } from "../severity";

export default function EquipmentCard({ eq }) {
  const navigate = useNavigate();
  const style = severityStyle(eq.severity);

  return (
    <button
      onClick={() => navigate(`/equipment/${eq.equipment_id}`)}
      className={`text-left w-full bg-base-900/80 border ${style.border} rounded-xl p-4 hover:shadow-glow hover:-translate-y-0.5 transition-all duration-150 group relative overflow-hidden`}
    >
      <div className={`absolute top-0 left-0 h-1 w-full ${style.dot} opacity-70`} />
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mono">{eq.equipment_id}</div>
          <div className="text-base font-semibold text-slate-100">{eq.name}</div>
          <div className="text-xs text-slate-500">{eq.type} · {eq.location}</div>
        </div>
        <div className={`px-2 py-0.5 rounded text-[11px] font-bold border ${style.text} ${style.bg} ${style.border}`}>
          {eq.severity}
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <div className="text-2xl font-bold mono text-slate-100">{eq.risk_score}<span className="text-sm text-slate-500">/100</span></div>
          <div className="text-xs text-slate-500">Failure prob. {(eq.failure_probability * 100).toFixed(0)}%</div>
        </div>
        <div className="text-right max-w-[55%]">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Suspected cause</div>
          <div className="text-xs text-slate-300 leading-tight">{eq.top_root_cause}</div>
        </div>
      </div>

      <div className="mt-3 h-1.5 rounded-full bg-base-800 overflow-hidden">
        <div className={`h-full ${style.dot}`} style={{ width: `${eq.risk_score}%` }} />
      </div>

      <div className="mt-2 text-[11px] text-slate-500 group-hover:text-signal-accent transition-colors">
        View investigation →
      </div>
    </button>
  );
}
