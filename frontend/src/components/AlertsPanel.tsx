import React from "react";
import { AlertItem } from "../types";

interface Props {
  alerts: AlertItem[];
  onUpdateStatus: (alertId: string, newStatus: "REVIEWED" | "DISMISSED" | "ESCALATED") => void;
}

export const AlertsPanel: React.FC<Props> = ({ alerts, onUpdateStatus }) => {
  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
          <h2 className="text-sm font-semibold tracking-wide text-rose-300 uppercase">
            Active SOC Fraud Alerts
          </h2>
        </div>
        <span className="text-xs text-rose-400/80 font-mono">
          {alerts.filter((a) => a.status === "OPEN").length} Open Alerts
        </span>
      </div>

      <div className="divide-y divide-slate-800/80 max-h-[520px] overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs font-mono">
            No active security incidents flagged. Stream monitoring nominal.
          </div>
        ) : (
          alerts.map((alt) => {
            const isCritical = alt.severity === "CRITICAL";
            const isHigh = alt.severity === "HIGH";

            return (
              <div
                key={alt.alert_id}
                className="p-4 hover:bg-slate-800/40 transition flex flex-col gap-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded tracking-wider border ${
                        isCritical
                          ? "bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse"
                          : isHigh
                          ? "bg-orange-500/20 text-orange-400 border-orange-500/40"
                          : "bg-amber-500/20 text-amber-400 border-amber-500/40"
                      }`}
                    >
                      {alt.severity}
                    </span>
                    <span className="text-xs font-mono font-semibold text-slate-200">
                      {alt.alert_id}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Risk: <span className="font-bold text-rose-400">{alt.risk_score.toFixed(1)}</span>
                  </span>
                </div>

                <div className="text-xs text-slate-300 flex items-center justify-between">
                  <span>
                    Txn: <span className="font-mono text-cyan-400">{alt.transaction_id}</span>
                  </span>
                  <span className="font-mono font-semibold text-slate-100">
                    ₹{alt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>

                {alt.reason_codes && alt.reason_codes.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {alt.reason_codes.map((rc, i) => (
                      <span
                        key={i}
                        className="bg-slate-800 text-slate-300 border border-slate-700 text-[10px] px-1.5 py-0.5 rounded font-mono"
                      >
                        {rc}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 mt-1">
                  <span className="text-[10px] text-slate-500 font-mono">
                    Status: <span className="text-slate-300">{alt.status}</span>
                  </span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => onUpdateStatus(alt.alert_id, "REVIEWED")}
                      className="px-2 py-0.5 text-[10px] bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 rounded transition"
                    >
                      Review
                    </button>
                    <button
                      onClick={() => onUpdateStatus(alt.alert_id, "ESCALATED")}
                      className="px-2 py-0.5 text-[10px] bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded transition"
                    >
                      Escalate
                    </button>
                    <button
                      onClick={() => onUpdateStatus(alt.alert_id, "DISMISSED")}
                      className="px-2 py-0.5 text-[10px] bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 rounded transition"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
