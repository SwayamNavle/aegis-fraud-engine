import React, { useState, useEffect, useRef } from "react";
import { KPICards } from "./components/KPICards";
import { LiveFeed } from "./components/LiveFeed";
import { AlertsPanel } from "./components/AlertsPanel";
import { ChartsView } from "./components/ChartsView";
import { SystemHealth } from "./components/SystemHealth";
import { TransactionModal } from "./components/TransactionModal";
import { TransactionItem, AlertItem, KPIStats, SystemStatusItem } from "./types";

export const App: React.FC = () => {
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [stats, setStats] = useState<KPIStats>({
    total_processed: 0,
    fraud_detected: 0,
    fraud_rate_pct: 0.0,
    avg_scoring_latency_ms: 1.25,
    active_alerts: 0,
    current_tps: 240.0,
  });
  const [throughputHistory, setThroughputHistory] = useState<
    Array<{ time: string; tps: number; latency_ms: number }>
  >([]);
  const [fraudData, setFraudData] = useState({
    decisions: [
      { name: "Legitimate", value: 980, color: "#10B981" },
      { name: "Suspicious", value: 14, color: "#F59E0B" },
      { name: "Fraud", value: 16, color: "#EF4444" },
    ],
    risk_distribution: [
      { range: "0-20 (Low)", count: 720 },
      { range: "20-40 (Normal)", count: 180 },
      { range: "40-60 (Elevated)", count: 45 },
      { range: "60-80 (Suspicious)", count: 25 },
      { range: "80-100 (Critical)", count: 18 },
    ],
    top_countries: [
      { country: "IN", count: 42 },
      { country: "GB", count: 15 },
      { country: "US", count: 9 },
    ],
  });
  const [selectedTxn, setSelectedTxn] = useState<TransactionItem | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  const systemServices: SystemStatusItem[] = [
    { name: "Kafka Broker", status: "ONLINE", mode: "KRaft Cluster", description: "Partitioned by account_id" },
    { name: "PySpark Streaming", status: "ONLINE", mode: "5m Slide (1m Window)", description: "Watermarked 10m" },
    { name: "XGBoost Engine", status: "ONLINE", mode: "xgb-v1.0.0", description: "Sub-2ms Inference SLA" },
    { name: "PostgreSQL", status: "ONLINE", mode: "ACID Idempotent", description: "Unique txn_id constraints" },
    { name: "Prometheus", status: "ONLINE", mode: "5s Polling", description: "Histogram latency metrics" },
  ];

  // Initialize REST data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const statsRes = await fetch("/stats");
        if (statsRes.ok) {
          const s = await statsRes.json();
          setStats((prev) => ({ ...prev, ...s }));
        }

        const tpRes = await fetch("/stats/throughput");
        if (tpRes.ok) {
          const tp = await tpRes.json();
          setThroughputHistory(tp);
        }

        const alertsRes = await fetch("/alerts?limit=20");
        if (alertsRes.ok) {
          const a = await alertsRes.json();
          setAlerts(a.items || []);
        }

        const txRes = await fetch("/transactions?limit=30");
        if (txRes.ok) {
          const t = await txRes.json();
          setTransactions(t.items || []);
        }
      } catch (err) {
        console.warn("Rest fetch error (using streaming defaults):", err);
      }
    };
    fetchInitialData();
  }, []);

  // Connect WebSocket for live streaming
  useEffect(() => {
    let ws: WebSocket;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    const wsUrl = `${protocol}//${host}/ws/transactions`;

    const connectWs = () => {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        console.log("[Aegis UI] Connected to live transaction stream.");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "TRANSACTION_EVENT") {
            const txn = data.transaction;
            setTransactions((prev) => [txn, ...prev.slice(0, 49)]);

            if (data.alert) {
              setAlerts((prev) => [data.alert, ...prev.slice(0, 29)]);
            }

            if (data.stats) {
              setStats((prev) => ({
                ...prev,
                total_processed: data.stats.total_processed,
                fraud_detected: data.stats.fraud_detected,
                fraud_rate_pct: data.stats.fraud_rate_pct,
                avg_scoring_latency_ms: data.stats.latest_latency_ms || prev.avg_scoring_latency_ms,
              }));
            }
          }
        } catch (e) {
          console.error("Failed to parse WS message:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWs, 2000);
      };
    };

    connectWs();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleUpdateAlertStatus = async (
    alertId: string,
    newStatus: "REVIEWED" | "DISMISSED" | "ESCALATED"
  ) => {
    try {
      await fetch(`/alerts/${alertId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      setAlerts((prev) =>
        prev.map((a) => (a.alert_id === alertId ? { ...a, status: newStatus } : a))
      );
    } catch (e) {
      console.error("Failed to update alert:", e);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Top Cyber Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-[#0a0f1d]/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center font-black text-white text-base shadow-lg shadow-cyan-500/20 tracking-tighter">
            AE
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black tracking-widest uppercase text-slate-100 font-mono">
                AEGIS COMMAND CENTER
              </h1>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-widest bg-cyan-950 border border-cyan-800 text-cyan-400">
                PROD-ENGINE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Distributed Event-Streaming &amp; Real-Time Fraud Engine
            </p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
            <span
              className={`w-2 h-2 rounded-full ${
                wsConnected ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className={wsConnected ? "text-emerald-400 font-semibold" : "text-rose-400"}>
              {wsConnected ? "STREAM LIVE" : "RECONNECTING"}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300">
            <span className="text-slate-500">MODEL:</span>
            <span className="text-cyan-400 font-bold">xgb-v1.0.0</span>
            <span className="text-slate-500 ml-1">THR:</span>
            <span className="text-amber-400 font-bold">0.70</span>
          </div>
        </div>
      </header>

      {/* Main Dashboard Workspace */}
      <main className="flex-1 p-6 max-w-[1680px] mx-auto w-full">
        {/* KPI Cards */}
        <KPICards stats={stats} />

        {/* Cluster Mesh Health */}
        <SystemHealth services={systemServices} />

        {/* Charts & Drift */}
        <ChartsView throughputData={throughputHistory} fraudData={fraudData} />

        {/* Live Transaction Feed & SOC Alert Triage */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <LiveFeed transactions={transactions} onSelectTransaction={setSelectedTxn} />
          </div>
          <div className="lg:col-span-1">
            <AlertsPanel alerts={alerts} onUpdateStatus={handleUpdateAlertStatus} />
          </div>
        </div>
      </main>

      {/* Transaction Modal Detail */}
      <TransactionModal transaction={selectedTxn} onClose={() => setSelectedTxn(null)} />
    </div>
  );
};

export default App;
