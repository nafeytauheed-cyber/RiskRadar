const STAGE_ICONS = {
  "Weak Signals": "◇",
  "Emerging Pattern": "∿",
  "Likely Root Cause": "⊙",
  "Predicted Failure Risk": "▲",
  "Safety Risk": "⚠",
  "Recommended Intervention": "✓",
};

export default function FailureChain({ steps }) {
  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-5">Failure-Chain Reasoning</h3>
      <div className="flex flex-col md:flex-row gap-0 md:gap-2 overflow-x-auto pb-2">
        {steps.map((step, i) => (
          <div key={i} className="flex md:flex-col items-stretch md:items-center flex-1 min-w-[150px]">
            <div className="flex-1 bg-base-850 border border-base-700/60 rounded-xl p-3.5 relative">
              <div className="w-7 h-7 rounded-full bg-base-800 border border-signal-accent/40 flex items-center justify-center text-signal-accent text-sm mb-2">
                {STAGE_ICONS[step.stage] || "•"}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{step.stage}</div>
              <div className="text-sm text-slate-200 leading-snug">{step.detail}</div>
            </div>
            {i < steps.length - 1 && (
              <div className="flex items-center justify-center md:rotate-90 px-2 md:px-0 md:py-2 text-slate-600 shrink-0">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M4 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
