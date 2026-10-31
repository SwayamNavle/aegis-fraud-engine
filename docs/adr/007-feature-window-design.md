# ADR 007: Sliding Window Aggregations, Event-Time Watermarking & Kinematics

## Context & Problem Statement
Real-time fraud detection relies heavily on statistical deviations from recent account behavior. A single ₹5,000 transaction is not inherently suspicious; however, four ₹5,000 transactions across different geographic regions within 3 minutes is a classic indicator of card cloning or credential stuffing. The system must compute sliding window aggregations across multiple time horizons and kinematic features (velocity, speed of travel) while strictly maintaining training-serving parity and bounding memory consumption.

## Decision
We standardized on a **canonical 20-feature specification** computed across sliding temporal windows (1-min, 5-min, 10-min, 30-min) with event-time watermarking and spherical trigonometric distance metrics (Haversine).

## Canonical Feature Set Architecture

The 20 features computed identically in both offline batch training (`features/offline_features.py`) and online streaming (`features/online_features.py`) are:

| Index | Feature Name | Computation Window | Description |
|:---:|:---|:---:|:---|
| 1 | `amount` | Point-in-time | Raw transaction currency value |
| 2 | `hour_of_day` | Point-in-time | Hour extracted from event timestamp (0–23) |
| 3 | `day_of_week` | Point-in-time | Day extracted from event timestamp (0–6) |
| 4 | `is_weekend` | Point-in-time | Binary flag (1 if Saturday/Sunday, else 0) |
| 5 | `card_present` | Point-in-time | Binary flag indicating physical chip/terminal vs CNP |
| 6 | `transaction_count_1m` | 1 minute | Count of transactions by account in last 60 seconds |
| 7 | `transaction_count_5m` | 5 minutes | Count of transactions by account in last 300 seconds |
| 8 | `transaction_count_10m` | 10 minutes | Count of transactions by account in last 600 seconds |
| 9 | `transaction_count_30m` | 30 minutes | Count of transactions by account in last 1800 seconds |
| 10 | `transaction_amount_sum_5m` | 5 minutes | Total currency spent by account in last 5 minutes |
| 11 | `transaction_amount_mean_5m` | 5 minutes | Mean spend amount by account in last 5 minutes |
| 12 | `transaction_amount_std_5m` | 5 minutes | Standard deviation of spend amount in last 5 minutes |
| 13 | `distance_from_last_txn_km` | Sequential | Spherical Haversine distance from previous transaction coordinates |
| 14 | `time_since_last_txn_sec` | Sequential | Elapsed seconds since immediate prior transaction |
| 15 | `geo_velocity_kmh` | Sequential | Kinematic speed ($\frac{\text{distance}}{\text{time}} \times 3600$) |
| 16 | `amount_to_mean_ratio_5m` | 5 minutes | Deviation ratio ($\frac{\text{amount}}{\text{transaction\_amount\_mean\_5m}}$) |
| 17 | `unique_merchants_30m` | 30 minutes | Distinct merchant IDs interacted with in last 30 minutes |
| 18 | `unique_countries_30m` | 30 minutes | Distinct ISO country codes in last 30 minutes |
| 19 | `failed_attempts_30m` | 30 minutes | Prior declined or failed transactions in last 30 minutes |
| 20 | `device_risk_score` | Point-in-time | Composite device security indicator (0.0–1.0) |

## Kinematic Math: Haversine & Impossible Travel
The distance between consecutive transactions $(\phi_1, \lambda_1)$ and $(\phi_2, \lambda_2)$ is calculated using the great-circle Haversine formula:
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$d = 2 R \cdot \arcsin\left(\sqrt{a}\right) \quad (R = 6,371\text{ km})$$
$$\text{velocity} = \frac{d}{\Delta t} \times 3,600 \text{ km/h}$$

If $\Delta t \le 60\text{ seconds}$ and $d > 50\text{ km}$, velocity exceeds commercial aviation speeds ($> 3,000\text{ km/h}$), immediately tripping the `IMPOSSIBLE_TRAVEL` rule violation.

## Memory Management & Watermarking
To prevent memory exhaustion when tracking millions of active customer sliding windows:
1. **Time-Based Eviction**: Events older than 30 minutes ($1,800\text{ seconds}$) are automatically trimmed from the deque/Redis list.
2. **Account Eviction**: Inactive accounts with no events for $> 24\text{ hours}$ are evicted from in-memory state stores to hot disk cache.
3. **Event-Time Watermarks**: Streaming pipelines apply a 10-minute watermark threshold. Events arriving older than 10 minutes past the watermark are routed directly to DLQ.

