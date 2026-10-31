export interface TransactionItem {
  transaction_id: string;
  correlation_id?: string;
  timestamp: string;
  user_id: string;
  account_id: string;
  amount: number;
  currency: string;
  merchant_id: string;
  merchant_category: string;
  country: string;
  city: string;
  fraud_probability?: number;
  risk_score: number;
  risk_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  business_decision?: "APPROVE" | "REVIEW" | "DECLINE";
  decision: "LEGITIMATE" | "SUSPICIOUS" | "FRAUD" | "APPROVE" | "REVIEW" | "DECLINE";
  latency_ms: number;
  reason_codes?: string[];
  rule_violations?: Array<{
    rule_id: string;
    severity: string;
    message: string;
    weight?: number;
  }>;
  feature_contributions?: Record<string, number>;
  decision_rationale?: string;
}

export interface AlertItem {
  alert_id: string;
  transaction_id: string;
  account_id: string;
  amount: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  fraud_probability?: number;
  reason_codes: string[];
  status: "OPEN" | "NEW" | "UNDER_REVIEW" | "REVIEWED" | "DISMISSED" | "ESCALATED" | "CONFIRMED_FRAUD" | "FALSE_POSITIVE";
  reviewer?: string;
  notes?: string;
  final_ground_truth?: string;
  decision_rationale?: string;
  timestamp?: string;
  created_at?: string;
}

export interface KPIStats {
  total_processed: number;
  total_transactions?: number;
  fraud_detected: number;
  suspicious_detected?: number;
  approved_count?: number;
  fraud_rate_pct: number;
  approval_rate_pct?: number;
  review_rate_pct?: number;
  decline_rate_pct?: number;
  avg_scoring_latency_ms: number;
  active_alerts: number;
  total_volume_inr?: number;
  estimated_fraud_exposure_inr?: number;
  average_transaction_amount_inr?: number;
  current_tps: number;
}

export interface SystemStatusItem {
  name: string;
  status: "ONLINE" | "WARNING" | "OFFLINE" | "STANDALONE_STREAM";
  mode: string;
  description: string;
}

export interface CustomerItem {
  account_id: string;
  user_id: string;
  total_transactions: number;
  total_spend: number;
  avg_amount: number;
  std_amount: number;
  max_amount: number;
  fraud_count: number;
  customer_risk_score: number;
  known_devices: string[];
  known_countries: string[];
}

export interface MerchantItem {
  merchant_id: string;
  merchant_name: string;
  category: string;
  total_transactions: number;
  total_volume: number;
  avg_amount: number;
  fraud_count: number;
  fraud_rate: number;
  merchant_risk_score: number;
}

export interface ModelItem {
  model_version: string;
  algorithm: string;
  training_timestamp: string;
  dataset_rows: number;
  fraud_threshold: number;
  metrics: Record<string, any>;
  model_path: string;
  status: "CANDIDATE" | "STAGING" | "PRODUCTION" | "ARCHIVED";
  is_active: boolean;
}
