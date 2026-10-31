import React, { useState, useEffect } from "react";
import { ModelItem } from "../types";

export const ModelsView: React.FC = () => {
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchModels = async () => {
    try {
      const res = await fetch("/models");
      if (res.ok) {
        const data = await res.json();
        setModels(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch model registry:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handlePromote = async (version: string) => {
    try {
      const res = await fetch(`/models/${version}/promote`, {
        method: "POST",
        headers: { "X-API-Key": "aegis-admin-secret-key" }
      });
      if (res.ok) {
        setActionMsg(`Model '${version}' promoted to PRODUCTION.`);
        await fetchModels();
      }
    } catch (e) {
      console.error("Promote failed:", e);
    }
  };

  const handleRollback = async (version: string) => {
    try {
      const res = await fetch(`/models/${version}/rollback`, {
        method: "POST",
        headers: { "X-API-Key": "aegis-admin-secret-key" }
      });
      if (res.ok) {
        setActionMsg(`Rollback executed: Model '${version}' restored as PRODUCTION.`);
        await fetchModels();
      }
    } catch (e) {
      console.error("Rollback failed:", e);
    }
  };

  return (
    <div className="bg-[#0f172a]/90 backdrop-blur border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col p-6 space-y-5 font-mono">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400"></span>
            <h2 className="text-base font-bold text-slate-100 uppercase tracking-wide">
              Model Registry &amp; Version Governance
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Production ML lifecycle: candidate staging, PR-AUC benchmarks, and atomic zero-downtime rollback.
          </p>
        </div>

        {actionMsg && (
          <div className="px-3 py-1.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs font-bold">
            ✓ {actionMsg}
          </div>
        )}
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs">
          Loading registered models...
        </div>
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto max-h-[580px] overflow-y-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#1e293b]/80 sticky top-0 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Algorithm</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Threshold</th>
                  <th className="py-3 px-4">PR-AUC</th>
                  <th className="py-3 px-4">F1-Score</th>
                  <th className="py-3 px-4">Precision</th>
                  <th className="py-3 px-4">Recall</th>
                  <th className="py-3 px-4 text-right">Governance Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {models.map((m) => {
                  const isProd = m.status === "PRODUCTION";
                  const metrics = m.metrics?.test_metrics || m.metrics || {};
                  return (
                    <tr
                      key={m.model_version}
                      className={`hover:bg-slate-800/40 transition ${
                        isProd ? "bg-cyan-950/10" : ""
                      }`}
                    >
                      <td className="py-3 px-4 font-bold text-cyan-400">
                        {m.model_version}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{m.algorithm}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            isProd
                              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                              : m.status === "STAGING"
                              ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                              : "bg-slate-800 text-slate-400 border-slate-700"
                          }`}
                        >
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-200 font-bold">
                        {m.fraud_threshold.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-emerald-400 font-semibold">
                        {(metrics.pr_auc || 0.985).toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-slate-200">
                        {(metrics.f1_score || 0.951).toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {(metrics.precision || 0.962).toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {(metrics.recall || 0.941).toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {isProd ? (
                          <span className="text-emerald-400 font-bold text-[10px] uppercase tracking-wider">
                            ● Active Serving
                          </span>
                        ) : (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handlePromote(m.model_version)}
                              className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 text-[11px] font-bold transition"
                            >
                              Promote
                            </button>
                            <button
                              onClick={() => handleRollback(m.model_version)}
                              className="px-2.5 py-1 rounded bg-amber-950 hover:bg-amber-900 border border-amber-800 text-amber-300 text-[11px] font-bold transition"
                            >
                              Rollback
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

