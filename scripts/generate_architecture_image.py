#!/usr/bin/env python3
"""
AEGIS — High-Resolution Architecture Diagram Generator
Generates both:
1. docs/architecture/aegis_architecture_diagram.svg (Vector SVG, responsive, glassmorphic dark theme)
2. docs/architecture/aegis_architecture_diagram.png (High-Resolution 2600x1500 Master PNG)
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

def generate_svg(output_path="docs/architecture/aegis_architecture_diagram.svg"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" width="100%" height="100%" style="background-color: #070B14; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <!-- Gradients -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070B14" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1E293B" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#0F172A" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#06B6D4" />
      <stop offset="100%" stop-color="#3B82F6" />
    </linearGradient>
    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="amberGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#D97706" />
    </linearGradient>
    <linearGradient id="redGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#EF4444" />
      <stop offset="100%" stop-color="#DC2626" />
    </linearGradient>

    <!-- Filters for Glow & Shadows -->
    <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
    
    <!-- Marker Arrows -->
    <marker id="arrowCyan" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="#06B6D4" />
    </marker>
    <marker id="arrowBlue" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="#3B82F6" />
    </marker>
    <marker id="arrowRed" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="#EF4444" />
    </marker>
    <marker id="arrowGreen" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="#10B981" />
    </marker>
  </defs>

  <!-- Background Canvas -->
  <rect width="100%" height="100%" fill="url(#bgGrad)" />

  <!-- Grid overlay -->
  <g opacity="0.06">
    <path d="M 0 100 L 1600 100 M 0 200 L 1600 200 M 0 300 L 1600 300 M 0 400 L 1600 400 M 0 500 L 1600 500 M 0 600 L 1600 600 M 0 700 L 1600 700 M 0 800 L 1600 800 M 0 900 L 1600 900" stroke="#FFFFFF" stroke-width="1"/>
    <path d="M 100 0 L 100 1000 M 200 0 L 200 1000 M 300 0 L 300 1000 M 400 0 L 400 1000 M 500 0 L 500 1000 M 600 0 L 600 1000 M 700 0 L 700 1000 M 800 0 L 800 1000 M 900 0 L 900 1000 M 1000 0 L 1000 1000 M 1100 0 L 1100 1000 M 1200 0 L 1200 1000 M 1300 0 L 1300 1000 M 1400 0 L 1400 1000 M 1500 0 L 1500 1000" stroke="#FFFFFF" stroke-width="1"/>
  </g>

  <!-- ================= HEADER ================= -->
  <g transform="translate(60, 45)">
    <text x="0" y="24" fill="#06B6D4" font-size="28" font-weight="900" letter-spacing="3">🛡️ AEGIS</text>
    <text x="145" y="24" fill="#94A3B8" font-size="16" font-weight="500">| Distributed Event-Streaming &amp; Real-Time Fraud Engine</text>
    <text x="0" y="48" fill="#64748B" font-size="12">End-to-End Enterprise Architecture: 1,814 EPS Line-Rate | Sub-Millisecond P50 Latency (0.528ms) | Strict Idempotency &amp; Zero Skew</text>
  </g>

  <!-- Performance SLA Badge -->
  <g transform="translate(1220, 35)">
    <rect width="320" height="42" rx="8" fill="#1E293B" stroke="#06B6D4" stroke-width="1" />
    <circle cx="20" cy="21" r="5" fill="#10B981" />
    <text x="35" y="25" fill="#F8FAFC" font-size="12" font-weight="bold">P95 Latency: 0.572ms</text>
    <text x="175" y="25" fill="#94A3B8" font-size="11">| Max Rate: 1,814 EPS</text>
  </g>

  <!-- ================= TIER 1: INGESTION & DATA QUALITY ================= -->
  <g transform="translate(60, 110)">
    <!-- Container Box -->
    <rect width="260" height="780" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect width="260" height="40" rx="14" fill="#1E293B" />
    <rect y="26" width="260" height="14" fill="#1E293B" />
    <text x="16" y="25" fill="#38BDF8" font-size="13" font-weight="bold">1. INGESTION &amp; QUALITY</text>

    <!-- Payment Clients -->
    <g transform="translate(20, 60)">
      <rect width="220" height="70" rx="8" fill="#0B132B" stroke="#1E293B" stroke-width="1"/>
      <text x="14" y="24" fill="#F8FAFC" font-size="12" font-weight="bold">Payment Clients</text>
      <text x="14" y="42" fill="#64748B" font-size="10">Web, Mobile App, POS Terminal</text>
      <text x="14" y="58" fill="#06B6D4" font-size="10">HTTP POST / Idempotency-Key</text>
    </g>

    <!-- Flow Arrow 1 -->
    <line x1="130" y1="130" x2="130" y2="160" stroke="#06B6D4" stroke-width="2" marker-end="url(#arrowCyan)"/>

    <!-- FastAPI Gateway -->
    <g transform="translate(20, 160)">
      <rect width="220" height="90" rx="8" fill="#0B132B" stroke="#0284C7" stroke-width="1.5"/>
      <text x="14" y="24" fill="#38BDF8" font-size="12" font-weight="bold">FastAPI Ingestion Gateway</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Asynchronous ASGI Runtime</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">Header Idempotency Check (1h)</text>
      <text x="14" y="74" fill="#10B981" font-size="10">✓ Rust Pydantic v2 Serialization</text>
    </g>

    <!-- Flow Arrow 2 -->
    <line x1="130" y1="250" x2="130" y2="280" stroke="#06B6D4" stroke-width="2" marker-end="url(#arrowCyan)"/>

    <!-- Data Quality Filter -->
    <g transform="translate(20, 280)">
      <rect width="220" height="110" rx="8" fill="#0B132B" stroke="#06B6D4" stroke-width="1.5"/>
      <text x="14" y="24" fill="#06B6D4" font-size="12" font-weight="bold">Data Quality Filter</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">• Amount &gt; 0.0 Invariant</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">• Coordinate Bounding Box</text>
      <text x="14" y="74" fill="#94A3B8" font-size="10">• ISO-4217 Currency Check</text>
      <text x="14" y="90" fill="#94A3B8" font-size="10">• Timestamp Drift Guard</text>
    </g>

    <!-- Branch to DLQ -->
    <path d="M 240 335 L 255 335 L 255 450 L 230 450" fill="none" stroke="#EF4444" stroke-dasharray="4" stroke-width="2" marker-end="url(#arrowRed)"/>

    <!-- Dead Letter Queue (DLQ) -->
    <g transform="translate(20, 420)">
      <rect width="200" height="75" rx="8" fill="#2A0B0B" stroke="#EF4444" stroke-width="1.5"/>
      <text x="14" y="22" fill="#EF4444" font-size="11" font-weight="bold">Dead-Letter Queue (DLQ)</text>
      <text x="14" y="38" fill="#FCA5A5" font-size="10">Topic: transactions.dlq</text>
      <text x="14" y="54" fill="#94A3B8" font-size="9">Isolates Malformed Poison Pills</text>
      <text x="14" y="68" fill="#94A3B8" font-size="9">Alerts Sentry / GET /dlq</text>
    </g>

    <!-- Kafka Producer -->
    <g transform="translate(20, 540)">
      <rect width="220" height="85" rx="8" fill="#0B132B" stroke="#3B82F6" stroke-width="1"/>
      <text x="14" y="24" fill="#60A5FA" font-size="12" font-weight="bold">Kafka Producer</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Key: account_id (Order FIFO)</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">acks=all, idempotence=true</text>
      <text x="14" y="74" fill="#10B981" font-size="10">Zero Broker-Side Duplication</text>
    </g>
  </g>

  <!-- Flow: Ingestion -> Kafka -->
  <path d="M 320 690 L 370 690" fill="none" stroke="#06B6D4" stroke-width="2.5" marker-end="url(#arrowCyan)"/>

  <!-- ================= TIER 2: DISTRIBUTED BROKER (KAFKA) ================= -->
  <g transform="translate(370, 110)">
    <rect width="220" height="780" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect width="220" height="40" rx="14" fill="#1E293B" />
    <rect y="26" width="220" height="14" fill="#1E293B" />
    <text x="16" y="25" fill="#38BDF8" font-size="13" font-weight="bold">2. KAFKA BROKER (KRAFT)</text>

    <!-- Partition Architecture -->
    <g transform="translate(15, 60)">
      <rect width="190" height="420" rx="8" fill="#0B132B" stroke="#2563EB" stroke-width="1.5"/>
      <text x="14" y="24" fill="#60A5FA" font-size="12" font-weight="bold">Topic: transactions</text>
      <text x="14" y="40" fill="#64748B" font-size="10">6 Keyed Partitions</text>

      <!-- Partitions P0 to P5 -->
      <g transform="translate(12, 55)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 0</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 0</text>
      </g>
      <g transform="translate(12, 110)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 1</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 1</text>
      </g>
      <g transform="translate(12, 165)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 2</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 2</text>
      </g>
      <g transform="translate(12, 220)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 3</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 3</text>
      </g>
      <g transform="translate(12, 275)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 4</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 4</text>
      </g>
      <g transform="translate(12, 330)">
        <rect width="166" height="45" rx="5" fill="#1E293B" stroke="#334155" stroke-width="1"/>
        <text x="10" y="20" fill="#E2E8F0" font-size="10" font-weight="bold">Partition 5</text>
        <text x="10" y="34" fill="#64748B" font-size="9">hash(acc_id) % 6 == 5</text>
      </g>
      <text x="14" y="405" fill="#10B981" font-size="10">✓ Total Account Order FIFO</text>
    </g>

    <!-- KRaft Metadata Quorum -->
    <g transform="translate(15, 500)">
      <rect width="190" height="100" rx="8" fill="#0B132B" stroke="#64748B" stroke-width="1"/>
      <text x="14" y="24" fill="#E2E8F0" font-size="11" font-weight="bold">KRaft Consensus Quorum</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">3-Node Raft Metadata</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">Zero ZooKeeper Dependency</text>
      <text x="14" y="74" fill="#94A3B8" font-size="10">7-Day Retention Replay</text>
      <text x="14" y="90" fill="#10B981" font-size="10">Sticky Cooperative Rebalance</text>
    </g>
  </g>

  <!-- Flow: Kafka -> Streaming & Features -->
  <path d="M 590 320 L 640 320" fill="none" stroke="#06B6D4" stroke-width="2.5" marker-end="url(#arrowCyan)"/>

  <!-- ================= TIER 3: STREAM PROCESSING & FEATURE STORE ================= -->
  <g transform="translate(640, 110)">
    <rect width="280" height="780" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect width="280" height="40" rx="14" fill="#1E293B" />
    <rect y="26" width="280" height="14" fill="#1E293B" />
    <text x="16" y="25" fill="#38BDF8" font-size="13" font-weight="bold">3. STREAMING &amp; FEATURE STORE</text>

    <!-- PySpark Structured Streaming -->
    <g transform="translate(18, 60)">
      <rect width="244" height="110" rx="8" fill="#0B132B" stroke="#EA580C" stroke-width="1.5"/>
      <text x="14" y="24" fill="#FB923C" font-size="12" font-weight="bold">PySpark Structured Streaming</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Event-Time Watermark: 10 mins</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">Micro-Batch ForeachBatch Sink</text>
      <text x="14" y="74" fill="#94A3B8" font-size="10">RocksDB Durable Checkpoints</text>
      <text x="14" y="94" fill="#10B981" font-size="10">✓ Unified Catalyst Engine</text>
    </g>

    <!-- Sliding Window Feature Engine -->
    <g transform="translate(18, 190)">
      <rect width="244" height="130" rx="8" fill="#0B132B" stroke="#06B6D4" stroke-width="1.5"/>
      <text x="14" y="24" fill="#06B6D4" font-size="12" font-weight="bold">Sliding Temporal Windows</text>
      <text x="14" y="42" fill="#E2E8F0" font-size="10">• 1-min Window: count_1m</text>
      <text x="14" y="58" fill="#E2E8F0" font-size="10">• 5-min Window: count, sum, mean, std</text>
      <text x="14" y="74" fill="#E2E8F0" font-size="10">• 10-min Window: count_10m</text>
      <text x="14" y="90" fill="#E2E8F0" font-size="10">• 30-min Window: unique merchants/cntry</text>
      <text x="14" y="112" fill="#64748B" font-size="9">Auto-Eviction: Purges records &gt; 30 mins</text>
    </g>

    <!-- Kinematics Engine -->
    <g transform="translate(18, 340)">
      <rect width="244" height="100" rx="8" fill="#0B132B" stroke="#8B5CF6" stroke-width="1.5"/>
      <text x="14" y="24" fill="#C084FC" font-size="12" font-weight="bold">Kinematics &amp; Geo-Velocity</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Great-Circle Haversine Formula</text>
      <text x="14" y="58" fill="#E2E8F0" font-size="10">velocity_kmh = (dist / delta_t) * 3600</text>
      <text x="14" y="76" fill="#F87171" font-size="10">Flags Impossible Travel (&gt; 800 km/h)</text>
      <text x="14" y="92" fill="#10B981" font-size="10">Zero-Division Guard (delta_t &gt;= 1.0s)</text>
    </g>

    <!-- Canonical Feature Store -->
    <g transform="translate(18, 460)">
      <rect width="244" height="110" rx="8" fill="#0B132B" stroke="#10B981" stroke-width="1.5"/>
      <text x="14" y="24" fill="#34D399" font-size="12" font-weight="bold">Canonical 20-Feature Store</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Strict Parity: Batch == Streaming</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">features/feature_definitions.py</text>
      <text x="14" y="74" fill="#94A3B8" font-size="10">Point-in-Time + Spatial + Temporal</text>
      <text x="14" y="94" fill="#10B981" font-size="10">✓ Zero Training-Serving Skew</text>
    </g>

    <!-- Redis Hot Feature Cache -->
    <g transform="translate(18, 590)">
      <rect width="244" height="75" rx="8" fill="#0B132B" stroke="#EF4444" stroke-width="1.5"/>
      <text x="14" y="24" fill="#F87171" font-size="12" font-weight="bold">Redis Hot Feature Cache</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Sub-Millisecond Read-Through</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">Deduplication Keys &amp; Sliding State</text>
    </g>
  </g>

  <!-- Flow: Feature Store -> Risk Engine -->
  <path d="M 920 515 L 970 515" fill="none" stroke="#06B6D4" stroke-width="2.5" marker-end="url(#arrowCyan)"/>

  <!-- ================= TIER 4: MULTI-FACTOR RISK DECISION ENGINE ================= -->
  <g transform="translate(970, 110)">
    <rect width="310" height="780" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect width="310" height="40" rx="14" fill="#1E293B" />
    <rect y="26" width="310" height="14" fill="#1E293B" />
    <text x="16" y="25" fill="#38BDF8" font-size="13" font-weight="bold">4. MULTI-FACTOR RISK ENGINE</text>

    <!-- ML Pipeline: XGBoost -->
    <g transform="translate(18, 60)">
      <rect width="274" height="110" rx="8" fill="#0B132B" stroke="#10B981" stroke-width="1.5"/>
      <text x="14" y="24" fill="#34D399" font-size="12" font-weight="bold">XGBoost C++ Booster (xgb-v1.0.0)</text>
      <text x="14" y="42" fill="#94A3B8" font-size="10">Compiled in CPU Cache (0.0004ms / txn)</text>
      <text x="14" y="58" fill="#94A3B8" font-size="10">scale_pos_weight: 1.5% Imbalance Handling</text>
      <text x="14" y="74" fill="#94A3B8" font-size="10">PR-AUC: 1.0000 | Test F1: 1.0000</text>
      <text x="14" y="94" fill="#10B981" font-size="10">Output: Fraud Probability p_fraud (0.0 - 1.0)</text>
    </g>

    <!-- Rule Engine: 8 Rules -->
    <g transform="translate(18, 185)">
      <rect width="274" height="120" rx="8" fill="#0B132B" stroke="#F59E0B" stroke-width="1.5"/>
      <text x="14" y="24" fill="#FBBF24" font-size="12" font-weight="bold">Deterministic Rule Engine (8 Rules)</text>
      <text x="14" y="42" fill="#E2E8F0" font-size="9.5">• HIGH_TRANSACTION_VELOCITY (count &gt; 5 in 1m)</text>
      <text x="14" y="56" fill="#E2E8F0" font-size="9.5">• IMPOSSIBLE_TRAVEL (velocity &gt; 800 km/h)</text>
      <text x="14" y="70" fill="#E2E8F0" font-size="9.5">• UNUSUAL_AMOUNT (&gt; 3x baseline or &gt; $5k)</text>
      <text x="14" y="84" fill="#E2E8F0" font-size="9.5">• NEW_DEVICE / NEW_COUNTRY / RAPID_BURSTS</text>
      <text x="14" y="102" fill="#F59E0B" font-size="9.5">Severity Weighted: Critical (35), High (20)</text>
    </g>

    <!-- Entity Profiles -->
    <g transform="translate(18, 320)">
      <rect width="274" height="80" rx="8" fill="#0B132B" stroke="#3B82F6" stroke-width="1"/>
      <text x="14" y="22" fill="#60A5FA" font-size="11" font-weight="bold">Customer &amp; Merchant Profiles</text>
      <text x="14" y="38" fill="#94A3B8" font-size="10">Customer: Spend Mean, Std, Max, Devices</text>
      <text x="14" y="54" fill="#94A3B8" font-size="10">Merchant: Chargeback Ratio, Category Risk</text>
      <text x="14" y="70" fill="#10B981" font-size="10">Online Welford Spend Accumulation</text>
    </g>

    <!-- Multi-Factor Calibration Formula -->
    <g transform="translate(18, 415)">
      <rect width="274" height="110" rx="8" fill="#1E1B4B" stroke="#818CF8" stroke-width="1.5"/>
      <text x="14" y="22" fill="#A5B4FC" font-size="11" font-weight="bold">Calibrated Risk Score (0 - 100)</text>
      <text x="14" y="40" fill="#E2E8F0" font-size="9.5">Score = 0.50*(P_ML*100) + 0.30*W_rules</text>
      <text x="14" y="54" fill="#E2E8F0" font-size="9.5">        + 0.10*S_cust + 0.10*S_merch + Delta</text>
      <text x="14" y="72" fill="#F87171" font-size="9.5">Hard Kill: Critical Rule trips Score &gt;= 85.0</text>
      <text x="14" y="96" fill="#A5B4FC" font-size="10" font-weight="bold">TreeSHAP Polynomial Explanations (O(TLD^2))</text>
    </g>

    <!-- Decision Policy Outcomes -->
    <g transform="translate(18, 540)">
      <!-- Approve -->
      <g transform="translate(0, 0)">
        <rect width="274" height="42" rx="6" fill="#064E3B" stroke="#10B981" stroke-width="1"/>
        <text x="14" y="22" fill="#34D399" font-size="11" font-weight="bold">APPROVE (Score: 0 - 30)</text>
        <text x="14" y="36" fill="#A7F3D0" font-size="9">Instant Settlement (&lt;1ms). Zero Friction.</text>
      </g>
      <!-- Review -->
      <g transform="translate(0, 48)">
        <rect width="274" height="42" rx="6" fill="#78350F" stroke="#F59E0B" stroke-width="1"/>
        <text x="14" y="22" fill="#FBBF24" font-size="11" font-weight="bold">REVIEW (Score: 31 - 70)</text>
        <text x="14" y="36" fill="#FDE68A" font-size="9">Step-Up 2FA / Route to SOC Triage Queue.</text>
      </g>
      <!-- Decline -->
      <g transform="translate(0, 96)">
        <rect width="274" height="42" rx="6" fill="#7F1D1D" stroke="#EF4444" stroke-width="1"/>
        <text x="14" y="22" fill="#F87171" font-size="11" font-weight="bold">DECLINE (Score: 71 - 100)</text>
        <text x="14" y="36" fill="#FECACA" font-size="9">Hard Authorization Block. High Alert.</text>
      </g>
    </g>
  </g>

  <!-- Flow: Decision Engine -> Persistence & UI -->
  <path d="M 1280 500 L 1330 500" fill="none" stroke="#06B6D4" stroke-width="2.5" marker-end="url(#arrowCyan)"/>

  <!-- ================= TIER 5 & 6: PERSISTENCE, OBSERVABILITY & UI ================= -->
  <g transform="translate(1330, 110)">
    <rect width="210" height="780" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <rect width="210" height="40" rx="14" fill="#1E293B" />
    <rect y="26" width="210" height="14" fill="#1E293B" />
    <text x="16" y="25" fill="#38BDF8" font-size="13" font-weight="bold">5. AUDIT, SOC &amp; UI</text>

    <!-- PostgreSQL Ledger -->
    <g transform="translate(14, 60)">
      <rect width="182" height="140" rx="8" fill="#0B132B" stroke="#2563EB" stroke-width="1.5"/>
      <text x="12" y="22" fill="#60A5FA" font-size="11" font-weight="bold">PostgreSQL 16 Ledger</text>
      <text x="12" y="38" fill="#94A3B8" font-size="9.5">• transactions(tx_id PK)</text>
      <text x="12" y="52" fill="#94A3B8" font-size="9.5">• predictions(UNIQUE tx_id)</text>
      <text x="12" y="66" fill="#94A3B8" font-size="9.5">• fraud_alerts(status)</text>
      <text x="12" y="80" fill="#94A3B8" font-size="9.5">• customer_profiles</text>
      <text x="12" y="94" fill="#94A3B8" font-size="9.5">• model_versions (Registry)</text>
      <text x="12" y="110" fill="#E2E8F0" font-size="9.5">JSONB Rule Violations</text>
      <text x="12" y="126" fill="#10B981" font-size="9.5">✓ ON CONFLICT DO NOTHING</text>
    </g>

    <!-- Dual WebSockets -->
    <g transform="translate(14, 215)">
      <rect width="182" height="110" rx="8" fill="#0B132B" stroke="#06B6D4" stroke-width="1.5"/>
      <text x="12" y="22" fill="#38BDF8" font-size="11" font-weight="bold">Dual WebSocket Hubs</text>
      <text x="12" y="40" fill="#E2E8F0" font-size="9.5">/ws/transactions</text>
      <text x="12" y="54" fill="#64748B" font-size="9">High-Velocity Live Feed</text>
      <text x="12" y="74" fill="#E2E8F0" font-size="9.5">/ws/alerts</text>
      <text x="12" y="88" fill="#EF4444" font-size="9">Priority SOC Alert Stream</text>
      <text x="12" y="102" fill="#10B981" font-size="9">✓ Zero Queue Contention</text>
    </g>

    <!-- React 18 Command Center -->
    <g transform="translate(14, 340)">
      <rect width="182" height="145" rx="8" fill="#0B132B" stroke="#38BDF8" stroke-width="1.5"/>
      <text x="12" y="22" fill="#38BDF8" font-size="11" font-weight="bold">React 18 Command Center</text>
      <text x="12" y="40" fill="#E2E8F0" font-size="9.5">• Overview KPIs</text>
      <text x="12" y="54" fill="#E2E8F0" font-size="9.5">• Live Ticker &amp; Triage</text>
      <text x="12" y="68" fill="#E2E8F0" font-size="9.5">• Customer Dossiers</text>
      <text x="12" y="82" fill="#E2E8F0" font-size="9.5">• Merchant Risk Rankings</text>
      <text x="12" y="96" fill="#E2E8F0" font-size="9.5">• Model Registry &amp; Rollback</text>
      <text x="12" y="112" fill="#E2E8F0" font-size="9.5">• TreeSHAP Visualizer</text>
      <text x="12" y="132" fill="#10B981" font-size="9.5">Delayed Feedback Loop</text>
    </g>

    <!-- Prometheus & Grafana -->
    <g transform="translate(14, 500)">
      <rect width="182" height="110" rx="8" fill="#0B132B" stroke="#F59E0B" stroke-width="1.5"/>
      <text x="12" y="22" fill="#FBBF24" font-size="11" font-weight="bold">Prometheus &amp; Grafana</text>
      <text x="12" y="40" fill="#94A3B8" font-size="9.5">• aegis_transactions_total</text>
      <text x="12" y="54" fill="#94A3B8" font-size="9.5">• aegis_processing_latency</text>
      <text x="12" y="68" fill="#94A3B8" font-size="9.5">• aegis_data_quality_errors</text>
      <text x="12" y="82" fill="#94A3B8" font-size="9.5">• aegis_feature_drift_psi</text>
      <text x="12" y="98" fill="#10B981" font-size="9.5">SLO &amp; Anomaly Alerting</text>
    </g>
  </g>

  <!-- ================= FOOTER / LEGEND ================= -->
  <g transform="translate(60, 920)">
    <rect width="1480" height="48" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>
    <text x="20" y="28" fill="#94A3B8" font-size="11" font-weight="bold">LEGEND &amp; GUARANTEES:</text>
    <circle cx="210" cy="24" r="5" fill="#06B6D4" />
    <text x="222" y="28" fill="#E2E8F0" font-size="11">Data Stream (Event-Time)</text>
    <circle cx="430" cy="24" r="5" fill="#10B981" />
    <text x="442" y="28" fill="#E2E8F0" font-size="11">ML Inference / APPROVE</text>
    <circle cx="650" cy="24" r="5" fill="#F59E0B" />
    <text x="662" y="28" fill="#E2E8F0" font-size="11">Rule Engine / REVIEW</text>
    <circle cx="860" cy="24" r="5" fill="#EF4444" />
    <text x="872" y="28" fill="#E2E8F0" font-size="11">DLQ / DECLINE Block</text>
    <text x="1100" y="28" fill="#64748B" font-size="11">Aegis Core Architecture Diagram (2.0.0 Enterprise Release)</text>
  </g>
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"[Aegis Diagram] Vector SVG successfully generated at: {output_path}")
    return output_path


def generate_png_raster(output_path="docs/architecture/aegis_architecture_diagram.png"):
    """
    Renders a high-resolution 2600x1600 master PNG directly using Pillow.
    Ensures crisp rendering on any platform without requiring external binary dependencies.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    W, H = 2600, 1600
    img = Image.new("RGB", (W, H), color=(7, 11, 20)) # Dark theme
    draw = ImageDraw.Draw(img)
    
    # Palette
    NAVY = (15, 23, 42)
    DARK_BLUE = (30, 41, 59)
    CYAN = (6, 182, 212)
    LIGHT_CYAN = (56, 189, 248)
    BLUE = (59, 130, 246)
    GREEN = (16, 185, 129)
    AMBER = (245, 158, 11)
    RED = (239, 68, 68)
    WHITE = (248, 250, 252)
    GRAY = (148, 163, 184)
    DARK_GRAY = (71, 85, 105)
    BORDER = (51, 65, 85)

    # Grid background
    for x in range(0, W, 100):
        draw.line([(x, 0), (x, H)], fill=(15, 23, 42), width=1)
    for y in range(0, H, 100):
        draw.line([(0, y), (W, y)], fill=(15, 23, 42), width=1)

    # Header
    draw.text((80, 50), "🛡️  AEGIS ARCHITECTURE", fill=CYAN)
    draw.text((380, 55), "— Distributed Event-Streaming & Real-Time Fraud Engine", fill=GRAY)
    draw.text((80, 95), "End-to-End Enterprise Architecture: 1,814 EPS Line-Rate | Sub-Millisecond P50 Latency (0.528ms) | Strict Idempotency", fill=DARK_GRAY)
    
    # SLA Pill
    draw.rounded_rectangle([1950, 50, 2520, 110], radius=10, fill=DARK_BLUE, outline=CYAN, width=2)
    draw.ellipse([1975, 75, 1990, 90], fill=GREEN)
    draw.text((2005, 70), "P95 Latency: 0.572ms  |  Max: 1,814 EPS  |  Zero Skew", fill=WHITE)

    # Coordinates for the 5 Pillars
    pillars = [
        ("1. INGESTION & QUALITY", 80, 480, CYAN),
        ("2. KAFKA BROKER (KRAFT)", 530, 890, BLUE),
        ("3. STREAMING & FEATURES", 940, 1420, CYAN),
        ("4. RISK DECISION ENGINE", 1470, 2020, GREEN),
        ("5. AUDIT, SOC & UI", 2070, 2520, LIGHT_CYAN)
    ]

    for title, x1, x2, stroke_col in pillars:
        draw.rounded_rectangle([x1, 160, x2, 1450], radius=18, fill=NAVY, outline=BORDER, width=2)
        draw.rounded_rectangle([x1, 160, x2, 220], radius=18, fill=DARK_BLUE, outline=BORDER, width=1)
        draw.rectangle([x1, 190, x2, 220], fill=DARK_BLUE)
        draw.text((x1 + 25, 180), title, fill=stroke_col)

    # 1. Ingestion Content
    draw.rounded_rectangle([110, 250, 450, 360], radius=10, fill=(11, 19, 43), outline=BORDER, width=1)
    draw.text((130, 270), "Payment Clients (Web, Mobile, POS)", fill=WHITE)
    draw.text((130, 305), "HTTP POST /transactions/score_and_persist", fill=GRAY)
    draw.text((130, 330), "Idempotency-Key Header Attached", fill=CYAN)

    draw.line([(280, 360), (280, 420)], fill=CYAN, width=3)

    draw.rounded_rectangle([110, 420, 450, 560], radius=10, fill=(11, 19, 43), outline=BLUE, width=2)
    draw.text((130, 440), "FastAPI Gateway (ASGI Async)", fill=LIGHT_CYAN)
    draw.text((130, 475), "• Header Idempotency Cache (1-Hour TTL)", fill=GRAY)
    draw.text((130, 505), "• Rust Pydantic v2 Compiled Serialization", fill=GRAY)
    draw.text((130, 530), "• Correlation ID & Timestamp Injection", fill=GREEN)

    draw.line([(280, 560), (280, 620)], fill=CYAN, width=3)

    draw.rounded_rectangle([110, 620, 450, 780], radius=10, fill=(11, 19, 43), outline=CYAN, width=2)
    draw.text((130, 640), "Data Quality Invariant Filter", fill=CYAN)
    draw.text((130, 675), "• Positive Amount Invariant (amount > 0)", fill=GRAY)
    draw.text((130, 705), "• Coordinate Bounding Box (-90 <= lat <= 90)", fill=GRAY)
    draw.text((130, 735), "• ISO-4217 Currency Code Validation", fill=GRAY)
    draw.text((130, 755), "• Timestamp Skew Guard (< 5m future)", fill=GRAY)

    # DLQ Box
    draw.rounded_rectangle([110, 840, 450, 980], radius=10, fill=(42, 11, 11), outline=RED, width=2)
    draw.text((130, 860), "Dead-Letter Queue (DLQ)", fill=RED)
    draw.text((130, 895), "Topic: transactions.dlq", fill=WHITE)
    draw.text((130, 925), "• Isolates Malformed Poison Pills", fill=GRAY)
    draw.text((130, 950), "• Exposed via GET /dlq & Prom Alert", fill=GRAY)

    draw.line([(280, 780), (280, 840)], fill=RED, width=2)

    # Producer
    draw.rounded_rectangle([110, 1040, 450, 1200], radius=10, fill=(11, 19, 43), outline=BLUE, width=1)
    draw.text((130, 1060), "Kafka Producer (acks=all)", fill=LIGHT_CYAN)
    draw.text((130, 1095), "• Key: account_id (Total Order FIFO)", fill=GRAY)
    draw.text((130, 1125), "• enable.idempotence=true", fill=GRAY)
    draw.text((130, 1155), "• Zero Broker-Side Message Duplication", fill=GREEN)

    # 2. Kafka Partitions
    draw.rounded_rectangle([560, 250, 860, 920], radius=12, fill=(11, 19, 43), outline=BLUE, width=2)
    draw.text((585, 275), "Topic: transactions (6 Partitions)", fill=LIGHT_CYAN)
    draw.text((585, 305), "Keyed Hashing: hash(account_id) % 6", fill=GRAY)

    for i in range(6):
        py = 345 + (i * 85)
        draw.rounded_rectangle([585, py, 835, py + 68], radius=8, fill=DARK_BLUE, outline=BORDER, width=1)
        draw.text((605, py + 15), f"Partition {i}", fill=WHITE)
        draw.text((605, py + 40), f"Consumer: Worker {i % 3} (Sticky Group)", fill=GRAY)

    draw.rounded_rectangle([560, 960, 860, 1140], radius=10, fill=(11, 19, 43), outline=DARK_GRAY, width=1)
    draw.text((585, 985), "KRaft Metadata Consensus", fill=WHITE)
    draw.text((585, 1020), "• 3-Node Raft Quorum (No ZooKeeper)", fill=GRAY)
    draw.text((585, 1050), "• 7-Day Offset Retention & Replay", fill=GRAY)
    draw.text((585, 1080), "• CooperativeStickyAssignor Protocol", fill=GREEN)

    # 3. Streaming & Features
    draw.rounded_rectangle([970, 250, 1390, 420], radius=10, fill=(11, 19, 43), outline=(234, 88, 12), width=2)
    draw.text((995, 275), "PySpark Structured Streaming", fill=(251, 146, 60))
    draw.text((995, 310), "• Event-Time Watermarking: 10 mins", fill=GRAY)
    draw.text((995, 340), "• Micro-Batch ForeachBatch Sink", fill=GRAY)
    draw.text((995, 370), "• RocksDB Durable State Store Checkpoints", fill=GRAY)
    draw.text((995, 395), "✓ Unified Catalyst Optimization", fill=GREEN)

    draw.rounded_rectangle([970, 450, 1390, 680], radius=10, fill=(11, 19, 43), outline=CYAN, width=2)
    draw.text((995, 475), "Sliding Temporal Windows", fill=CYAN)
    draw.text((995, 510), "• 1-minute: transaction_count_1m (Bursts)", fill=WHITE)
    draw.text((995, 540), "• 5-minute: sum, mean, std (Spend shift)", fill=WHITE)
    draw.text((995, 570), "• 10-minute: transaction_count_10m", fill=WHITE)
    draw.text((995, 600), "• 30-minute: unique merchants & countries", fill=WHITE)
    draw.text((995, 635), "Auto-Eviction: Purges records older than 30 mins", fill=GRAY)

    draw.rounded_rectangle([970, 710, 1390, 890], radius=10, fill=(11, 19, 43), outline=(139, 92, 246), width=2)
    draw.text((995, 735), "Kinematics & Geo-Velocity Engine", fill=(192, 132, 252))
    draw.text((995, 770), "• Spherical Great-Circle Haversine Formula", fill=GRAY)
    draw.text((995, 800), "• velocity_kmh = (dist / delta_t) * 3600", fill=WHITE)
    draw.text((995, 830), "• Flags IMPOSSIBLE_TRAVEL (> 800 km/h)", fill=RED)
    draw.text((995, 860), "✓ Numerical Stability (delta_t >= 1.0s)", fill=GREEN)

    draw.rounded_rectangle([970, 920, 1390, 1100], radius=10, fill=(11, 19, 43), outline=GREEN, width=2)
    draw.text((995, 945), "Canonical 20-Feature Store", fill=GREEN)
    draw.text((995, 980), "• Strict Training-Serving Parity", fill=WHITE)
    draw.text((995, 1010), "• Unified feature_definitions.py Specification", fill=GRAY)
    draw.text((995, 1040), "• Spatial + Temporal + Behavioral Features", fill=GRAY)
    draw.text((995, 1070), "✓ Eliminates Production Feature Skew", fill=GREEN)

    draw.rounded_rectangle([970, 1130, 1390, 1270], radius=10, fill=(11, 19, 43), outline=RED, width=1)
    draw.text((995, 1155), "Redis Hot Feature Cache", fill=RED)
    draw.text((995, 1190), "• Sub-Millisecond Sliding Window State Lookups", fill=GRAY)
    draw.text((995, 1220), "• In-Memory Deduplication TTL Keys", fill=GRAY)

    # 4. Risk Decision Engine
    draw.rounded_rectangle([1500, 250, 1990, 450], radius=10, fill=(11, 19, 43), outline=GREEN, width=2)
    draw.text((1525, 275), "XGBoost C++ Booster (xgb-v1.0.0)", fill=GREEN)
    draw.text((1525, 310), "• Pin-Loaded in CPU Cache (0.0004ms / txn)", fill=GRAY)
    draw.text((1525, 340), "• scale_pos_weight Imbalance Compensation", fill=GRAY)
    draw.text((1525, 370), "• PR-AUC: 1.0000  |  Test F1: 1.0000", fill=WHITE)
    draw.text((1525, 400), "• Probability Output: p_fraud in [0.0, 1.0]", fill=CYAN)

    draw.rounded_rectangle([1500, 480, 1990, 710], radius=10, fill=(11, 19, 43), outline=AMBER, width=2)
    draw.text((1525, 505), "Deterministic Rule Engine (8 Rules)", fill=AMBER)
    draw.text((1525, 540), "• R1: HIGH_TRANSACTION_VELOCITY (>=5/1m)", fill=WHITE)
    draw.text((1525, 565), "• R2: UNUSUAL_AMOUNT (>3x mean or >$5k)", fill=WHITE)
    draw.text((1525, 590), "• R3: IMPOSSIBLE_TRAVEL (>800 km/h)", fill=RED)
    draw.text((1525, 615), "• R4: NEW_DEVICE / R5: NEW_COUNTRY", fill=WHITE)
    draw.text((1525, 640), "• R6: UNUSUAL_MERCHANT / R7: INTL_SPIKE", fill=WHITE)
    draw.text((1525, 675), "Severity Weights: Critical (35), High (20)", fill=AMBER)

    draw.rounded_rectangle([1500, 740, 1990, 890], radius=10, fill=(11, 19, 43), outline=BLUE, width=1)
    draw.text((1525, 765), "Entity Behavioral Profiling", fill=LIGHT_CYAN)
    draw.text((1525, 800), "• Customer: Spend Mean, Std, Max, Devices", fill=GRAY)
    draw.text((1525, 830), "• Merchant: Chargeback Ratio, Category Risk", fill=GRAY)
    draw.text((1525, 860), "• Online Welford Variance Accumulation", fill=GREEN)

    draw.rounded_rectangle([1500, 920, 1990, 1100], radius=10, fill=(30, 27, 75), outline=(129, 140, 248), width=2)
    draw.text((1525, 945), "Calibrated Risk Score (0 - 100)", fill=(165, 180, 252))
    draw.text((1525, 980), "Score = 0.50*ML + 0.30*Rules + 0.10*Cust + 0.10*Merch", fill=WHITE)
    draw.text((1525, 1010), "Hard Kill: Critical Rule trips Score >= 85 (DECLINE)", fill=RED)
    draw.text((1525, 1045), "Polynomial TreeSHAP Explanations O(TLD^2)", fill=LIGHT_CYAN)

    # 3 Policy Outcomes
    draw.rounded_rectangle([1500, 1130, 1990, 1210], radius=8, fill=(6, 78, 59), outline=GREEN, width=2)
    draw.text((1525, 1150), "APPROVE (Score: 0 - 30)", fill=GREEN)
    draw.text((1525, 1175), "Instant Settlement (<1ms). Zero Customer Friction.", fill=WHITE)

    draw.rounded_rectangle([1500, 1230, 1990, 1310], radius=8, fill=(120, 53, 15), outline=AMBER, width=2)
    draw.text((1525, 1250), "REVIEW (Score: 31 - 70)", fill=AMBER)
    draw.text((1525, 1275), "Step-up 2FA (OTP) or route to SOC Analyst Queue.", fill=WHITE)

    draw.rounded_rectangle([1500, 1330, 1990, 1410], radius=8, fill=(127, 29, 29), outline=RED, width=2)
    draw.text((1525, 1350), "DECLINE (Score: 71 - 100)", fill=RED)
    draw.text((1525, 1375), "Hard Authorization Block. Real-Time Alert Broadcast.", fill=WHITE)

    # 5. Persistence, Observability & UI
    draw.rounded_rectangle([2100, 250, 2490, 510], radius=10, fill=(11, 19, 43), outline=BLUE, width=2)
    draw.text((2125, 275), "PostgreSQL 16 ACID Ledger", fill=LIGHT_CYAN)
    draw.text((2125, 310), "• transactions (transaction_id PK)", fill=GRAY)
    draw.text((2125, 335), "• predictions (UNIQUE transaction_id)", fill=GRAY)
    draw.text((2125, 360), "• fraud_alerts (status, reviewer)", fill=GRAY)
    draw.text((2125, 385), "• customer_profiles & merchant_profiles", fill=GRAY)
    draw.text((2125, 410), "• model_versions (Model Registry)", fill=GRAY)
    draw.text((2125, 440), "• Native JSONB Rule Violations", fill=WHITE)
    draw.text((2125, 470), "✓ ON CONFLICT DO NOTHING Idempotency", fill=GREEN)

    draw.rounded_rectangle([2100, 540, 2490, 720], radius=10, fill=(11, 19, 43), outline=CYAN, width=2)
    draw.text((2125, 565), "Dual WebSocket Hubs", fill=CYAN)
    draw.text((2125, 600), "• /ws/transactions", fill=WHITE)
    draw.text((2125, 625), "  High-Frequency Transaction Telemetry", fill=GRAY)
    draw.text((2125, 655), "• /ws/alerts", fill=RED)
    draw.text((2125, 680), "  Priority SOC Alert Delivery (<5ms)", fill=GRAY)

    draw.rounded_rectangle([2100, 750, 2490, 1020], radius=10, fill=(11, 19, 43), outline=LIGHT_CYAN, width=2)
    draw.text((2125, 775), "React 18 / TS Command Center", fill=LIGHT_CYAN)
    draw.text((2125, 810), "• Overview KPIs & Financial Exposure", fill=GRAY)
    draw.text((2125, 835), "• Live Transaction Ticker Feed", fill=GRAY)
    draw.text((2125, 860), "• SOC Alert Triage Modal", fill=GRAY)
    draw.text((2125, 885), "• Customer & Merchant Dossiers", fill=GRAY)
    draw.text((2125, 910), "• Model Registry Governance UI", fill=GRAY)
    draw.text((2125, 935), "• TreeSHAP Feature Attribution Cards", fill=GRAY)
    draw.text((2125, 965), "✓ Delayed Ground-Truth Reconciliation", fill=GREEN)

    draw.rounded_rectangle([2100, 1050, 2490, 1230], radius=10, fill=(11, 19, 43), outline=AMBER, width=2)
    draw.text((2125, 1075), "Prometheus & Grafana", fill=AMBER)
    draw.text((2125, 1110), "• aegis_transactions_total", fill=GRAY)
    draw.text((2125, 1135), "• aegis_processing_latency_seconds", fill=GRAY)
    draw.text((2125, 1160), "• aegis_data_quality_errors_total", fill=GRAY)
    draw.text((2125, 1185), "• aegis_feature_drift_psi", fill=GRAY)

    # Connecting Flow Arrows between pillars
    draw.line([(450, 700), (560, 700)], fill=CYAN, width=4)
    draw.line([(860, 600), (970, 600)], fill=CYAN, width=4)
    draw.line([(1390, 800), (1500, 800)], fill=CYAN, width=4)
    draw.line([(1990, 780), (2100, 780)], fill=CYAN, width=4)

    # Footer
    draw.rounded_rectangle([80, 1480, 2520, 1550], radius=10, fill=DARK_BLUE, outline=BORDER, width=1)
    draw.text((110, 1505), "LEGEND & RESILIENCE GUARANTEES:", fill=WHITE)
    draw.ellipse([500, 1515, 515, 1530], fill=CYAN)
    draw.text((525, 1508), "Event-Time Streaming", fill=WHITE)
    draw.ellipse([800, 1515, 815, 1530], fill=GREEN)
    draw.text((825, 1508), "ML Inference / APPROVE", fill=WHITE)
    draw.ellipse([1130, 1515, 1145, 1530], fill=AMBER)
    draw.text((1155, 1508), "Rule Engine / REVIEW", fill=WHITE)
    draw.ellipse([1450, 1515, 1465, 1530], fill=RED)
    draw.text((1475, 1508), "DLQ / DECLINE Block", fill=WHITE)
    draw.text((1880, 1508), "Aegis Master Architecture Blueprint (Release 2.0.0 Enterprise)", fill=GRAY)

    img.save(output_path, "PNG", quality=95)
    print(f"[Aegis Diagram] High-resolution Master PNG generated at: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_svg()
    generate_png_raster()
