import React from "react";
import { TransactionItem } from "../types";

interface Props {
  transaction: TransactionItem | null;
  onClose: () => void;
}

export const TransactionModal: React.FC<Props> = ({ transaction, onClose }) => {
  if (!transaction) return null;

  const isDecline = transaction.business_decision === "DECLINE" || transaction.decision === "FRAUD";
  const isReview = transaction.business_decision === "REVIEW" || transaction.decision === "SUSPICIOUS";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="bg-[#0b1120] border border-slate-700/80 w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest bg-cyan-950/80 border border-cyan-800/80 px-2 py-0.5 rounded">
                TRANSACTION DOSSIER
              </span>
              {transaction.correlation_id && (
                <span className="text-[10px] font-mono text-slate-400">
                  trace: {transaction.correlation_id.slice(0, 12)}...
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold font-mono text-slate-100 mt-1">
              {transaction.transaction_id}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 flex items-center justify-center transition border border-slate-700"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono">
          {/* Top Score & Decision Banner */}
          <div
            className={`p-5 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
              isDecline
                ? "bg-rose-950/40 border-rose-800/60 text-rose-200"
                : isReview
                ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
            }`}
          >
            <div>
              <div className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                Business Decision &amp; Risk Verdict
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-2xl font-black tracking-wide">
                  {transaction.business_decision || transaction.decision}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                    isDecline
                      ? "bg-rose-900/60 border-rose-600 text-rose-100"
                      : isReview
                      ? "bg-amber-900/60 border-amber-600 text-amber-100"
                      : "bg-emerald-900/60 border-emerald-600 text-emerald-100"
                  }`}
                >
                  {transaction.risk_level || "EVALUATED"}
                </span>
              </div>
              {transaction.decision_rationale && (
                <p className="text-[11px] mt-1.5 opacity-90 max-w-md">
                  {transaction.decision_rationale}
                </p>
              )}
            </div>
            <div className="md:text-right">
              <div className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                Composite Risk Score
              </div>
              <div className="text-3xl font-black mt-0.5">
                {transaction.risk_score.toFixed(1)}
                <span className="text-sm font-normal opacity-70"> / 100</span>
              </div>
              {transaction.fraud_probability !== undefined && (
                <div className="text-[10px] opacity-75 mt-0.5">
                  ML Model Probability: {(transaction.fraud_probability * 100).toFixed(1)}%
                </div>
              )}
            </div>
          </div>

          {/* Triggered Rule Violations */}
          {transaction.reason_codes && transaction.reason_codes.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                Triggered Rule Engine Violations
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {transaction.reason_codes.map((code, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-rose-950/20 border border-rose-800/40 text-rose-300 flex items-start gap-2"
                  >
                    <span className="text-rose-400 text-sm">⚠️</span>
                    <div>
                      <div className="font-bold text-[11px]">{code}</div>
                      <div className="text-[10px] text-rose-300/80 mt-0.5">
                        Violation detected by deterministic heuristic rules
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SHAP Feature Contributions */}
          {transaction.feature_contributions &&
            Object.keys(transaction.feature_contributions).length > 0 && (
              <div>
                <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2 flex items-center justify-between">
                  <span>TreeSHAP Feature Risk Drivers</span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    Model Log-Odds Attribution
                  </span>
                </div>
                <div className="space-y-2 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                  {Object.entries(transaction.feature_contributions).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-300 font-medium">{k}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-28 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${v >= 0 ? "bg-rose-500" : "bg-emerald-500"}`}
                            style={{ width: `${Math.min(100, Math.abs(v) * 60)}%` }}
                          />
                        </div>
                        <span
                          className={`font-bold w-14 text-right ${
                            v >= 0 ? "text-rose-400" : "text-emerald-400"
                          }`}
                        >
                          {v >= 0 ? `+${v.toFixed(3)}` : v.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Core Transaction Metadata */}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
              Payment &amp; Device Metadata
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <div>
                <span className="text-slate-500 block text-[10px]">ACCOUNT ID</span>
                <span className="text-slate-200 font-semibold">{transaction.account_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">USER ID</span>
                <span className="text-slate-200 font-semibold">{transaction.user_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">AMOUNT</span>
                <span className="text-emerald-400 font-bold text-sm">
                  ₹{transaction.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">MERCHANT</span>
                <span className="text-slate-200 font-semibold">
                  {transaction.merchant_id} ({transaction.merchant_category})
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ORIGIN</span>
                <span className="text-slate-200 font-semibold">
                  {transaction.city}, {transaction.country}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">TIMESTAMP</span>
                <span className="text-slate-300 text-[10px]">{transaction.timestamp}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-[11px] text-slate-400">
          <span>Scoring Latency: {transaction.latency_ms.toFixed(3)} ms</span>
          <span>Decision Engine: Multi-Factor ML + Rules v2.0</span>
        </div>
      </div>
    </div>
  );
};
