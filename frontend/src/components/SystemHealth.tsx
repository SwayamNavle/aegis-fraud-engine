import React from "react";
import { SystemStatusItem } from "../types";

interface Props {
  services: SystemStatusItem[];
}

export const SystemHealth: React.FC<Props> = ({ services }) => {
  return (
    <div className="bg-[#0f172a]/80 backdrop-blur border border-slate-800 rounded-xl p-4 shadow-lg mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Infrastructure &amp; Pipeline Mesh Health
        </h3>
        <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Cluster Nominal
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex flex-col gap-1"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-200 truncate">{svc.name}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            </div>
            <div className="text-[10px] text-cyan-400 font-semibold">{svc.mode}</div>
            <div className="text-[9px] text-slate-500 truncate">{svc.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
