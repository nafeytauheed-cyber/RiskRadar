import { Link } from "react-router-dom";

export default function Header({ subtitle }) {
  return (
    <header className="border-b border-base-700/60 bg-base-950/80 backdrop-blur sticky top-0 z-20 no-print">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-signal-accent to-blue-600 flex items-center justify-center shadow-glow">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="3" fill="white" />
              <circle cx="12" cy="12" r="8" stroke="white" strokeWidth="1.5" opacity="0.7" />
              <circle cx="12" cy="12" r="11" stroke="white" strokeWidth="1" opacity="0.35" />
            </svg>
          </div>
          <div>
            <div className="text-lg font-extrabold tracking-tight text-slate-100 leading-none">RiskRadar</div>
            <div className="text-[10px] uppercase tracking-[0.15em] text-slate-500">AI Safety Investigator</div>
          </div>
        </Link>
        {subtitle && <div className="text-sm text-slate-400 mono hidden md:block">{subtitle}</div>}
      </div>
    </header>
  );
}
