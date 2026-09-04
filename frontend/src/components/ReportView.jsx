import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { severityStyle } from "../severity";
import FailureChain from "./FailureChain";

export default function ReportView() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.equipmentReport(id).then(setReport).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="p-10 text-red-400">{error}</div>;
  if (!report) return <div className="p-10 text-slate-500 mono">Compiling report…</div>;

  const style = severityStyle(report.severity);

  return (
    <div className="min-h-screen bg-base-950">
      <div className="no-print border-b border-base-700/60 bg-base-900/60 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to={`/equipment/${id}`} className="text-xs text-slate-500 hover:text-slate-300">← Back to investigation</Link>
          <button
            onClick={() => window.print()}
            className="px-4 py-2 rounded-lg bg-signal-accent/15 border border-signal-accent/40 text-signal-accent text-sm font-semibold hover:bg-signal-accent/25"
          >
            Download / Print PDF
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10 print:py-0">
        <div className="mb-8 pb-6 border-b border-base-700/60">
          <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500 mb-2">RiskRadar · Automated Safety Investigation Report</div>
          <h1 className="text-2xl font-bold text-slate-100 mb-2">{report.title}</h1>
          <div className="text-xs text-slate-500 mono">Generated {new Date(report.generated_at).toLocaleString()}</div>
        </div>

        <Section title="Executive Summary">
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-bold mb-3 ${style.text} ${style.bg} ${style.border}`}>
            {report.severity.toUpperCase()} · RISK {report.risk_score}/100 · {report.urgency}
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">{report.summary}</p>
        </Section>

        <Section title="Failure-Chain Reasoning">
          <FailureChain steps={report.failure_chain} />
        </Section>

        <Section title="Root Cause Analysis">
          <p className="text-sm text-slate-300 leading-relaxed mb-3">{report.root_cause.description}</p>
          {report.root_cause.candidates?.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 text-xs uppercase tracking-wider">
                  <th className="pb-2">Candidate Cause</th>
                  <th className="pb-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {report.root_cause.candidates.map((c) => (
                  <tr key={c.root_cause} className="border-t border-base-700/50">
                    <td className="py-1.5 text-slate-300">{c.label}</td>
                    <td className="py-1.5 text-slate-400 mono">{(c.confidence * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        <Section title="Supporting Evidence">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 text-xs uppercase tracking-wider">
                <th className="pb-2">Signal</th>
                <th className="pb-2">Current</th>
                <th className="pb-2">Normal Range</th>
                <th className="pb-2">Deviation</th>
              </tr>
            </thead>
            <tbody>
              {report.evidence.map((e) => (
                <tr key={e.metric} className="border-t border-base-700/50">
                  <td className="py-1.5 text-slate-300">{e.metric}</td>
                  <td className="py-1.5 text-slate-400 mono">{e.current_value} {e.unit}</td>
                  <td className="py-1.5 text-slate-500 mono">{e.normal_range[0]}–{e.normal_range[1]}</td>
                  <td className="py-1.5 text-slate-400 mono">{e.deviation_std > 0 ? "+" : ""}{e.deviation_std}σ</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        {report.similar_incidents.length > 0 && (
          <Section title="Comparable Historical Incidents">
            <ul className="space-y-2">
              {report.similar_incidents.map((s) => (
                <li key={s.incident_id} className="text-sm text-slate-300">
                  <span className="mono text-slate-500">{s.incident_id}</span> — {s.similarity_pct}% similar ·
                  {" "}{s.equipment_type}, root cause: {s.root_cause.replaceAll("_", " ")} · resolved by: {s.action_taken}
                </li>
              ))}
            </ul>
          </Section>
        )}

        <Section title="Recommended Action Plan">
          {report.action_plan.map((group) => (
            <div key={group.priority} className="mb-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">{group.priority}</div>
              <ul className="space-y-1">
                {group.items.map((item, i) => (
                  <li key={i} className="text-sm text-slate-300">• {item}</li>
                ))}
              </ul>
            </div>
          ))}
        </Section>

        <Section title="Event Timeline">
          <ul className="space-y-1.5">
            {report.timeline.map((ev, i) => (
              <li key={i} className="text-sm text-slate-300">
                <span className="mono text-slate-500 mr-2">{ev.date}</span>{ev.label}
              </li>
            ))}
          </ul>
        </Section>

        <div className="text-center text-[11px] text-slate-600 mt-12 pt-6 border-t border-base-700/60">
          Generated by RiskRadar — AI-powered industrial safety investigation system. For decision support only; verify findings with qualified personnel before acting.
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500 mb-3">{title}</h2>
      {children}
    </div>
  );
}
