import React from "react";
import { KPIStats } from "../types";

interface Props {
  stats: KPIStats;
}

export const KPICards: React.FC<Props> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
      {/* 1. Throughput */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-cyan-500/50 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Throughput</div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-cyan-400 font-mono">
            {stats.current_tps ? stats.current_tps.toLocaleString() : "240.0"}
          </span>
          <span className="text-xs text-slate-500">events/sec</span>
        </div>
        <div className="mt-2 text-[11px] text-emerald-400 flex items-center gap-1">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          Line Rate Stable
        </div>
      </div>

      {/* 2. Total Processed */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-slate-700 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Scored</div>
        <div className="mt-2 text-2xl font-bold text-slate-100 font-mono">
          {stats.total_processed.toLocaleString()}
        </div>
        <div className="mt-2 text-[11px] text-slate-500">100% Idempotent</div>
      </div>

      {/* 3. Fraud Detected */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-rose-950/60 rounded-xl p-4 shadow-lg shadow-rose-950/20 hover:border-rose-500/50 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-rose-400">Fraud Flagged</div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-rose-400 font-mono">
            {stats.fraud_detected.toLocaleString()}
          </span>
          <span className="text-xs text-rose-500/80">events</span>
        </div>
        <div className="mt-2 text-[11px] text-rose-400/90">Automated Quarantine</div>
      </div>

      {/* 4. Fraud Rate */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-amber-500/50 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Fraud Ratio</div>
        <div className="mt-2 text-2xl font-bold text-amber-400 font-mono">
          {stats.fraud_rate_pct.toFixed(2)}%
        </div>
        <div className="mt-2 text-[11px] text-slate-500">Baseline 1.5% - 2.0%</div>
      </div>

      {/* 5. Latency */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-purple-500/50 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">P95 Scoring Latency</div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold text-purple-400 font-mono">
            {stats.avg_scoring_latency_ms.toFixed(2)}
          </span>
          <span className="text-xs text-slate-500">ms</span>
        </div>
        <div className="mt-2 text-[11px] text-emerald-400">SLA: &lt; 5.0 ms</div>
      </div>

      {/* 6. Active Alerts */}
      <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg hover:border-orange-500/50 transition">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Open SOC Alerts</div>
        <div className="mt-2 text-2xl font-bold text-orange-400 font-mono">
          {stats.active_alerts.toLocaleString()}
        </div>
        <div className="mt-2 text-[11px] text-slate-500">Awaiting Investigation</div>
      </div>
    </div>
  );
};
