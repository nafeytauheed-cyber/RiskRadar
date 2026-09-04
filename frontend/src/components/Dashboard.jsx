import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Header from "./Header";
import RiskGauge from "./RiskGauge";
import KpiCard from "./KpiCard";
import EquipmentCard from "./EquipmentCard";
import { severityStyle } from "../severity";

const FILTERS = ["All", "Critical", "High", "Medium", "Low"];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("All");

  useEffect(() => {
    api.overview().then(setData).catch((e) => setError(e.message));
  }, []);

  const equipment = useMemo(() => {
    if (!data) return [];
    if (filter === "All") return data.equipment;
    return data.equipment.filter((e) => e.severity === filter);
  }, [data, filter]);

  if (error) return <ErrorScreen message={error} />;
  if (!data) return <LoadingScreen />;

  return (
    <div className="min-h-screen">
      <Header subtitle={`Fleet scan · ${data.total_equipment} units · updated ${new Date(data.generated_at).toLocaleString()}`} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-6 mb-8">
          <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6 flex items-center gap-6 lg:w-[380px]">
            <RiskGauge score={data.overall_risk_score} severity={data.overall_severity} label="Overall System Risk" size={140} />
            <div className="flex-1">
              <div className="text-sm text-slate-400 leading-relaxed">
                Aggregate safety risk across the monitored fleet, weighted by equipment criticality and failure likelihood.
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
            <KpiCard label="Total Equipment" value={data.total_equipment} />
            <KpiCard label="High Risk (High+Critical)" value={data.high_risk_count} accent="text-amber-400" />
            <KpiCard label="Critical" value={data.severity_counts.Critical} accent="text-red-400" />
            <KpiCard label="Healthy (Low)" value={data.severity_counts.Low} accent="text-emerald-400" />
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Equipment Under Investigation</h2>
          <div className="flex gap-1 bg-base-900/80 border border-base-700/60 rounded-lg p-1">
            {FILTERS.map((f) => {
              const active = filter === f;
              const style = f !== "All" ? severityStyle(f) : null;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    active ? "bg-base-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {f}
                  {f !== "All" && (
                    <span className={`ml-1.5 ${style.text}`}>{data.severity_counts[f]}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {equipment.map((eq) => (
            <EquipmentCard key={eq.equipment_id} eq={eq} />
          ))}
        </div>

        {equipment.length === 0 && (
          <div className="text-center text-slate-500 py-16">No equipment matches this filter.</div>
        )}
      </main>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-signal-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <div className="text-slate-400 text-sm mono">Scanning fleet telemetry…</div>
      </div>
    </div>
  );
}

function ErrorScreen({ message }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <div className="text-red-400 font-semibold mb-2">Could not reach RiskRadar API</div>
        <div className="text-sm text-slate-500 mono">{message}</div>
        <div className="text-xs text-slate-600 mt-4">Make sure the backend is running on port 8000.</div>
      </div>
    </div>
  );
}
