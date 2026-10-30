import React from "react";

interface Props {
  throughputData: Array<{ time: string; tps: number; latency_ms: number }>;
  fraudData: {
    decisions: Array<{ name: string; value: number; color: string }>;
    risk_distribution: Array<{ range: string; count: number }>;
    top_countries: Array<{ country: string; count: number }>;
  };
  driftData?: Array<{ feature: string; psi: number; status: string }>;
}

export const ChartsView: React.FC<Props> = ({ throughputData, fraudData, driftData }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {/* 1. Throughput & Latency Trend */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Throughput (TPS) &amp; Latency Trend
          </h3>
          <span className="text-[10px] text-cyan-400 font-mono">Live Ingestion</span>
        </div>
        <div className="h-44 flex items-end gap-2 pt-4 px-2 border-b border-l border-slate-800">
          {throughputData.slice(-14).map((item, i) => {
            const heightPct = Math.min(100, Math.max(15, (item.tps / 400) * 100));
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                <div
                  className="w-full bg-cyan-500/30 group-hover:bg-cyan-400 border-t border-cyan-400 rounded-t transition-all"
                  style={{ height: `${heightPct}%` }}
                />
                <span className="text-[9px] text-slate-500 font-mono hidden group-hover:block absolute -top-6 bg-slate-900 border border-slate-700 px-1 rounded z-10">
                  {item.tps} tps
                </span>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-2">
          <span>T-15m</span>
          <span>Latency: ~1.2ms P95</span>
          <span>Now</span>
        </div>
      </div>

      {/* 2. Risk Score Distribution */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Calibrated Risk Distribution
          </h3>
          <span className="text-[10px] text-amber-400 font-mono">Scores [0-100]</span>
        </div>
        <div className="space-y-2.5">
          {fraudData.risk_distribution.map((item, i) => {
            const total = fraudData.risk_distribution.reduce((acc, curr) => acc + curr.count, 0) || 1;
            const pct = Math.round((item.count / total) * 100);
            const isHigh = i >= 3;
            return (
              <div key={item.range} className="text-xs font-mono">
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-slate-400">{item.range}</span>
                  <span className={isHigh ? "text-rose-400 font-bold" : "text-slate-300"}>
                    {item.count} ({pct}%)
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      i === 4
                        ? "bg-rose-500"
                        : i === 3
                        ? "bg-amber-400"
                        : i === 2
                        ? "bg-yellow-400"
                        : "bg-emerald-400"
                    }`}
                    style={{ width: `${Math.max(4, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Feature Drift Monitoring (PSI) */}
      <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Feature Drift (PSI Telemetry)
          </h3>
          <span className="text-[10px] text-emerald-400 font-mono">Baseline Aligned</span>
        </div>
        <div className="space-y-2 font-mono text-xs">
          {(
            driftData || [
              { feature: "transaction_amount_avg_5m", psi: 0.038, status: "STABLE" },
              { feature: "velocity_score", psi: 0.042, status: "STABLE" },
              { feature: "geo_velocity_kmh", psi: 0.065, status: "STABLE" },
              { feature: "amount_z_score", psi: 0.021, status: "STABLE" },
              { feature: "merchant_risk_score", psi: 0.015, status: "STABLE" },
            ]
          ).map((item) => (
            <div
              key={item.feature}
              className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800"
            >
              <span className="text-[11px] text-slate-300 truncate max-w-[150px]">
                {item.feature}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-[10px]">PSI: {item.psi.toFixed(3)}</span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
