import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const SENSORS = [
  { key: "vibration", label: "Vibration", color: "#f59e0b" },
  { key: "temperature", label: "Temperature", color: "#ef4444" },
  { key: "pressure", label: "Pressure", color: "#38bdf8" },
  { key: "current", label: "Current", color: "#a78bfa" },
  { key: "rpm", label: "RPM", color: "#22c55e" },
];

export default function SensorTrendChart({ data }) {
  const [active, setActive] = useState("vibration");
  const sensor = SENSORS.find((s) => s.key === active);

  return (
    <div className="bg-base-900/80 border border-base-700/60 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Sensor Trend (recent cycles)</h3>
        <div className="flex gap-1">
          {SENSORS.map((s) => (
            <button
              key={s.key}
              onClick={() => setActive(s.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                active === s.key ? "bg-base-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2233" />
          <XAxis dataKey="cycle" stroke="#4b5c73" fontSize={11} />
          <YAxis stroke="#4b5c73" fontSize={11} />
          <Tooltip
            contentStyle={{ background: "#131926", border: "1px solid #243044", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Line type="monotone" dataKey={sensor.key} stroke={sensor.color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
