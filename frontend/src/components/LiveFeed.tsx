import React from "react";
import { TransactionItem } from "../types";

interface Props {
  transactions: TransactionItem[];
  onSelectTransaction: (txn: TransactionItem) => void;
}

export const LiveFeed: React.FC<Props> = ({ transactions, onSelectTransaction }) => {
  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase">
            Live Stream Inspection Feed
          </h2>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Showing latest {transactions.length} events
        </span>
      </div>

      <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-[#1e293b]/70 sticky top-0 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Transaction ID</th>
              <th className="py-3 px-4">Account</th>
              <th className="py-3 px-4">Amount</th>
              <th className="py-3 px-4">Merchant</th>
              <th className="py-3 px-4">Origin</th>
              <th className="py-3 px-4">Risk Score</th>
              <th className="py-3 px-4">Decision</th>
              <th className="py-3 px-4 text-right">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {transactions.map((txn) => {
              const isFraud = txn.decision === "FRAUD";
              const isSuspicious = txn.decision === "SUSPICIOUS";

              return (
                <tr
                  key={txn.transaction_id}
                  onClick={() => onSelectTransaction(txn)}
                  className={`cursor-pointer transition hover:bg-slate-800/50 ${
                    isFraud
                      ? "bg-rose-950/20 hover:bg-rose-950/40"
                      : isSuspicious
                      ? "bg-amber-950/10 hover:bg-amber-950/30"
                      : ""
                  }`}
                >
                  <td className="py-2.5 px-4 font-semibold text-cyan-400">
                    {txn.transaction_id}
                  </td>
                  <td className="py-2.5 px-4 text-slate-300">
                    {txn.account_id}
                  </td>
                  <td className="py-2.5 px-4 font-semibold text-slate-100">
                    ₹{txn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="py-2.5 px-4 text-slate-300">
                    <span className="text-slate-200">{txn.merchant_id}</span>
                    <span className="text-[10px] text-slate-500 block">{txn.merchant_category}</span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-300">
                    {txn.city}, {txn.country}
                  </td>
                  <td className="py-2.5 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            isFraud
                              ? "bg-rose-500"
                              : isSuspicious
                              ? "bg-amber-400"
                              : "bg-emerald-400"
                          }`}
                          style={{ width: `${Math.min(100, txn.risk_score)}%` }}
                        />
                      </div>
                      <span
                        className={`text-xs font-bold ${
                          isFraud
                            ? "text-rose-400"
                            : isSuspicious
                            ? "text-amber-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {txn.risk_score.toFixed(1)}
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider ${
                        isFraud
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : isSuspicious
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {txn.decision}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right text-slate-400 text-[11px]">
                    {txn.latency_ms.toFixed(2)} ms
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
