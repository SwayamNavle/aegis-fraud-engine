import React, { useState, useEffect } from "react";
import { MerchantItem } from "../types";

export const MerchantsView: React.FC = () => {
  const [merchants, setMerchants] = useState<MerchantItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  useEffect(() => {
    const fetchMerchants = async () => {
      try {
        const res = await fetch("/merchants?limit=100");
        if (res.ok) {
          const data = await res.json();
          setMerchants(data.items || []);
        }
      } catch (e) {
        console.error("Failed to fetch merchants:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchMerchants();
  }, []);

  const categories = ["ALL", ...Array.from(new Set(merchants.map((m) => m.category)))];

  const filtered = merchants.filter(
    (m) => selectedCategory === "ALL" || m.category === selectedCategory
  );

  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col p-6 space-y-5 font-mono">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <h2 className="text-base font-bold text-slate-100 uppercase tracking-wide">
              Merchant Risk Profiling &amp; Fraud Exposure
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Terminal transaction volumes, category risk indices, and observed historical chargeback rates.
          </p>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto text-xs">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded transition text-[11px] whitespace-nowrap ${
                selectedCategory === cat
                  ? "bg-cyan-950 border border-cyan-800 text-cyan-300 font-bold"
                  : "bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {cat.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          Loading merchant risk dossiers...
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          No merchant profiles recorded for this category.
        </div>
      ) : (
        <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#1e293b]/80 sticky top-0 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Merchant ID</th>
                <th className="py-3 px-4">Terminal Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Total Volume</th>
                <th className="py-3 px-4">Txn Count</th>
                <th className="py-3 px-4">Fraud Count</th>
                <th className="py-3 px-4">Fraud Rate</th>
                <th className="py-3 px-4 text-right">Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.map((m) => {
                const isHighRisk = m.merchant_risk_score >= 60.0;
                return (
                  <tr key={m.merchant_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-cyan-400 font-bold">{m.merchant_id}</td>
                    <td className="py-3 px-4 text-slate-200 font-semibold">{m.merchant_name}</td>
                    <td className="py-3 px-4 text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px]">
                        {m.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-emerald-400 font-bold">
                      ₹{m.total_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-slate-100">{m.total_transactions}</td>
                    <td className="py-3 px-4">
                      {m.fraud_count > 0 ? (
                        <span className="text-rose-400 font-bold bg-rose-950/60 border border-rose-800/80 px-2 py-0.5 rounded text-[10px]">
                          {m.fraud_count} Fraud
                        </span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-semibold">
                      {m.fraud_rate.toFixed(2)}%
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`px-2.5 py-1 rounded text-[11px] font-bold border ${
                          isHighRisk
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                        }`}
                      >
                        {m.merchant_risk_score.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

