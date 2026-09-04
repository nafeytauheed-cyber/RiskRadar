export default function KpiCard({ label, value, sub, accent = "text-slate-100" }) {
  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-xl p-4">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">{label}</div>
      <div className={`text-3xl font-bold mono ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}
