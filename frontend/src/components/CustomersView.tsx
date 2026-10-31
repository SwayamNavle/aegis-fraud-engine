import React, { useState, useEffect } from "react";
import { CustomerItem } from "../types";

export const CustomersView: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        const res = await fetch("/customers?limit=100");
        if (res.ok) {
          const data = await res.json();
          setCustomers(data.items || []);
        }
      } catch (e) {
        console.error("Failed to fetch customers:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchCustomers();
  }, []);

  const filtered = customers.filter(
    (c) =>
      c.account_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.user_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col p-6 space-y-5 font-mono">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <h2 className="text-base font-bold text-slate-100 uppercase tracking-wide">
              Customer Intelligence &amp; Behavioral Profiles
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Historical transaction patterns, normal spend distributions, device graphs, and risk scores.
          </p>
        </div>

        <input
          type="text"
          placeholder="Filter by account or user ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-slate-900 border border-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:border-cyan-500 w-full md:w-72"
        />
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          Loading customer behavioral profiles...
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          No customer profiles recorded matching criteria.
        </div>
      ) : (
        <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#1e293b]/80 sticky top-0 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Account ID</th>
                <th className="py-3 px-4">User ID</th>
                <th className="py-3 px-4">Transactions</th>
                <th className="py-3 px-4">Avg Spend</th>
                <th className="py-3 px-4">Peak Spend</th>
                <th className="py-3 px-4">Fraud Count</th>
                <th className="py-3 px-4">Known Devices</th>
                <th className="py-3 px-4">Countries</th>
                <th className="py-3 px-4 text-right">Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.map((c) => {
                const isHighRisk = c.customer_risk_score >= 50.0;
                return (
                  <tr key={c.account_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-cyan-400 font-bold">{c.account_id}</td>
                    <td className="py-3 px-4 text-slate-300">{c.user_id}</td>
                    <td className="py-3 px-4 text-slate-100">{c.total_transactions}</td>
                    <td className="py-3 px-4 text-slate-300">
                      ₹{c.avg_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-emerald-400 font-semibold">
                      ₹{c.max_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4">
                      {c.fraud_count > 0 ? (
                        <span className="text-rose-400 font-bold bg-rose-950/60 border border-rose-800/80 px-2 py-0.5 rounded text-[10px]">
                          {c.fraud_count} Flagged
                        </span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {c.known_devices.length > 0 ? `${c.known_devices.length} registered` : "None"}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {c.known_countries.join(", ") || "IN"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`px-2.5 py-1 rounded text-[11px] font-bold border ${
                          isHighRisk
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                        }`}
                      >
                        {c.customer_risk_score.toFixed(1)}
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

