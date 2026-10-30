import React from "react";
import { TransactionItem } from "../types";

interface Props {
  transaction: TransactionItem | null;
  onClose: () => void;
}

export const TransactionModal: React.FC<Props> = ({ transaction, onClose }) => {
  if (!transaction) return null;

  const isFraud = transaction.decision === "FRAUD";
  const isSuspicious = transaction.decision === "SUSPICIOUS";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0f172a] border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Transaction Dossier
            </div>
            <h3 className="text-lg font-bold font-mono text-cyan-400">
              {transaction.transaction_id}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center transition"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono">
          {/* Top Score Banner */}
          <div
            className={`p-4 rounded-xl border flex items-center justify-between ${
              isFraud
                ? "bg-rose-950/40 border-rose-800/60 text-rose-200"
                : isSuspicious
                ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
            }`}
          >
            <div>
              <div className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                Inference Verdict
              </div>
              <div className="text-xl font-extrabold tracking-wide mt-0.5">
                {transaction.decision}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                Calibrated Risk Score
              </div>
              <div className="text-2xl font-black mt-0.5">
                {transaction.risk_score.toFixed(1)} / 100
              </div>
            </div>
          </div>

          {/* Reason Codes */}
          {transaction.reason_codes && transaction.reason_codes.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                Deterministic Fraud Reason Codes
              </div>
              <div className="flex flex-wrap gap-2">
                {transaction.reason_codes.map((code, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[11px] font-bold"
                  >
                    ⚠️ {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Feature Contributions / Explainability */}
          {transaction.feature_contributions &&
            Object.keys(transaction.feature_contributions).length > 0 && (
              <div>
                <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                  Top Feature Risk Drivers (Model Weights)
                </div>
                <div className="space-y-1.5 bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                  {Object.entries(transaction.feature_contributions).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-300">{k}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-cyan-400 h-full"
                            style={{ width: `${Math.min(100, (v / 8.0) * 100)}%` }}
                          />
                        </div>
                        <span className="text-cyan-400 font-bold w-12 text-right">
                          +{v.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Core Transaction Metadata */}
          <div className="grid grid-cols-2 gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
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
              <span className="text-slate-300 text-[11px]">{transaction.timestamp}</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/40 flex items-center justify-between text-[11px] text-slate-500">
          <span>Inference Latency: {transaction.latency_ms.toFixed(3)} ms</span>
          <span>Engine: Aegis XGBoost v1.0.0</span>
        </div>
      </div>
    </div>
  );
};
