import React, { useState } from "react";
import { AlertItem } from "../types";

interface Props {
  alerts: AlertItem[];
  onUpdateStatus: (alertId: string, newStatus: any, reviewer?: string, notes?: string) => void;
}

export const AlertsPanel: React.FC<Props> = ({ alerts, onUpdateStatus }) => {
  const [filter, setFilter] = useState<string>("ALL");

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "ALL") return true;
    if (filter === "OPEN") return a.status === "OPEN" || a.status === "NEW" || a.status === "UNDER_REVIEW";
    return a.status === filter;
  });

  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col h-full">
      {/* Panel Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
            <h2 className="text-sm font-semibold tracking-wide text-rose-300 uppercase font-mono">
              SOC Fraud Triage Queue
            </h2>
          </div>
          <span className="text-xs text-rose-400 font-mono font-bold bg-rose-950/60 border border-rose-800/60 px-2 py-0.5 rounded">
            {alerts.filter((a) => a.status === "NEW" || a.status === "OPEN" || a.status === "UNDER_REVIEW").length} Pending
          </span>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono">
          {["ALL", "OPEN", "CONFIRMED_FRAUD", "FALSE_POSITIVE"].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-2.5 py-1 rounded transition whitespace-nowrap ${
                filter === tab
                  ? "bg-slate-700 text-cyan-300 font-bold border border-cyan-800"
                  : "bg-slate-900/80 text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Stream */}
      <div className="divide-y divide-slate-800/80 max-h-[560px] overflow-y-auto flex-1">
        {filteredAlerts.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs font-mono">
            No alerts matching filter. All transactions within nominal parameters.
          </div>
        ) : (
          filteredAlerts.map((alt) => {
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
                      className={`text-[10px] font-bold px-2 py-0.5 rounded tracking-wider border font-mono ${
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

                <div className="text-xs text-slate-300 flex items-center justify-between font-mono">
                  <span>
                    Txn: <span className="text-cyan-400">{alt.transaction_id}</span>
                  </span>
                  <span className="font-semibold text-emerald-400">
                    ₹{alt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>

                {alt.reason_codes && alt.reason_codes.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {alt.reason_codes.map((rc, i) => (
                      <span
                        key={i}
                        className="bg-slate-900 border border-slate-700 text-rose-300 text-[10px] px-1.5 py-0.5 rounded font-mono"
                      >
                        {rc}
                      </span>
                    ))}
                  </div>
                )}

                {alt.reviewer && (
                  <div className="text-[10px] text-slate-400 font-mono">
                    Investigated by: <span className="text-cyan-400">{alt.reviewer}</span>
                  </div>
                )}

                {/* Workflow Status & Triage Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 mt-1">
                  <span className="text-[10px] text-slate-400 font-mono">
                    Status:{" "}
                    <span
                      className={`font-bold ${
                        alt.status === "CONFIRMED_FRAUD"
                          ? "text-rose-400"
                          : alt.status === "FALSE_POSITIVE"
                          ? "text-emerald-400"
                          : alt.status === "UNDER_REVIEW"
                          ? "text-amber-400"
                          : "text-slate-200"
                      }`}
                    >
                      {alt.status}
                    </span>
                  </span>

                  <div className="flex gap-1.5">
                    {alt.status !== "CONFIRMED_FRAUD" && alt.status !== "FALSE_POSITIVE" && (
                      <>
                        <button
                          onClick={() => onUpdateStatus(alt.alert_id, "UNDER_REVIEW", "analyst_1", "Under active review")}
                          className="px-2 py-0.5 text-[10px] font-mono bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 rounded transition"
                        >
                          Review
                        </button>
                        <button
                          onClick={() => onUpdateStatus(alt.alert_id, "CONFIRMED_FRAUD", "analyst_1", "Confirmed fraudulent card takeover")}
                          className="px-2 py-0.5 text-[10px] font-mono bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded transition font-bold"
                        >
                          Fraud
                        </button>
                        <button
                          onClick={() => onUpdateStatus(alt.alert_id, "FALSE_POSITIVE", "analyst_1", "Legitimate travel purchase confirmed with cardholder")}
                          className="px-2 py-0.5 text-[10px] font-mono bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 rounded transition"
                        >
                          Legit
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => onUpdateStatus(alt.alert_id, "DISMISSED")}
                      className="px-2 py-0.5 text-[10px] font-mono bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 rounded transition"
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
