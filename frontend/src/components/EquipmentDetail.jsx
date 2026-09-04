import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../api";
import Header from "./Header";
import RiskGauge from "./RiskGauge";
import FailureChain from "./FailureChain";
import EvidencePanel from "./EvidencePanel";
import Timeline from "./Timeline";
import SimilarIncidents from "./SimilarIncidents";
import RecommendedActions from "./RecommendedActions";
import SensorTrendChart from "./SensorTrendChart";
import { severityStyle } from "../severity";

export default function EquipmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    api.equipmentDetail(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="p-10 text-red-400">{error}</div>;
  if (!data) return <div className="p-10 text-slate-500 mono">Loading investigation…</div>;

  const style = severityStyle(data.severity);

  return (
    <div className="min-h-screen">
      <Header subtitle={data.equipment_id} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Link to="/" className="no-print text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-4">
          ← Back to fleet overview
        </Link>

        <div className={`bg-base-900/80 border ${style.border} rounded-2xl p-6 mb-6 flex flex-col md:flex-row gap-6 items-center`}>
          <RiskGauge score={data.risk_score} severity={data.severity} size={150} label="Individual Equipment Risk" />
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap mb-1">
              <h1 className="text-2xl font-bold text-slate-100">{data.name}</h1>
              <span className="text-xs text-slate-500 mono">{data.equipment_id}</span>
            </div>
            <div className="text-sm text-slate-400 mb-3">
              {data.type} · {data.location} · Criticality: {data.criticality} · Installed {data.install_date}
            </div>
            <div className="grid grid-cols-3 gap-4 max-w-md">
              <Metric label="Failure Prob." value={`${data.risk_components.failure_probability_pct}%`} />
              <Metric label="Anomaly Score" value={data.risk_components.anomaly_score} />
              <Metric label="Root-Cause Conf." value={`${data.risk_components.root_cause_confidence_pct}%`} />
            </div>
          </div>
        </div>

        <div className="mb-6">
          <FailureChain steps={data.failure_chain} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2 space-y-6">
            <SensorTrendChart data={data.sensor_trend} />
            <EvidencePanel evidence={data.evidence} summary={data.evidence_summary} modelDrivers={data.model_drivers} />
            <Timeline events={data.timeline} />
          </div>
          <div className="space-y-6">
            <SimilarIncidents incidents={data.similar_incidents} />
            <RecommendedActions
              actions={data.recommended_actions}
              onGenerateReport={() => navigate(`/equipment/${id}/report`)}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-lg font-bold mono text-slate-100">{value}</div>
    </div>
  );
}
