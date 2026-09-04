import { severityStyle } from "../severity";

export default function RiskGauge({ score, severity, size = 160, label = "Risk Score" }) {
  const style = severityStyle(severity);
  const radius = (size - 20) / 2;
  const circumference = Math.PI * radius; // half circle
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const dash = circumference * pct;
  const cx = size / 2;
  const cy = size / 2 + 6;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 24} viewBox={`0 0 ${size} ${size / 2 + 24}`}>
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="#1a2233"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={style.hex}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          style={{ filter: `drop-shadow(0 0 6px ${style.hex}66)` }}
        />
        <text x={cx} y={cy - 18} textAnchor="middle" className="mono" fill="#e5edf7" fontSize="30" fontWeight="700">
          {score}
        </text>
        <text x={cx} y={cy + 2} textAnchor="middle" fill="#7a8ba3" fontSize="11">
          / 100
        </text>
      </svg>
      <div className={`mt-1 px-3 py-1 rounded-full text-xs font-semibold border ${style.text} ${style.bg} ${style.border}`}>
        {severity?.toUpperCase()}
      </div>
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mt-1">{label}</div>
    </div>
  );
}
