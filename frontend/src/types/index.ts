export interface TransactionItem {
  transaction_id: string;
  timestamp: string;
  user_id: string;
  account_id: string;
  amount: number;
  currency: string;
  merchant_id: string;
  merchant_category: string;
  country: string;
  city: string;
  risk_score: number;
  decision: "LEGITIMATE" | "SUSPICIOUS" | "FRAUD";
  latency_ms: number;
  reason_codes?: string[];
  feature_contributions?: Record<string, number>;
}

export interface AlertItem {
  alert_id: string;
  transaction_id: string;
  account_id: string;
  amount: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  reason_codes: string[];
  status: "OPEN" | "REVIEWED" | "DISMISSED" | "ESCALATED";
  timestamp?: string;
  created_at?: string;
}

export interface KPIStats {
  total_processed: number;
  fraud_detected: number;
  suspicious_detected?: number;
  fraud_rate_pct: number;
  avg_scoring_latency_ms: number;
  active_alerts: number;
  current_tps: number;
}

export interface SystemStatusItem {
  name: string;
  status: "ONLINE" | "WARNING" | "OFFLINE" | "STANDALONE_STREAM";
  mode: string;
  description: string;
}
