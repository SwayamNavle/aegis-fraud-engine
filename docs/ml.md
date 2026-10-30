# Aegis Machine Learning & Fraud Detection Pipeline

## 1. Problem Formulation & Class Imbalance

Financial fraud detection is characterized by **severe class imbalance**:
- In production financial networks, legitimate transactions comprise 98.5% to 99.5% of total volume.
- In our empirical 50,000-event training dataset, the fraud prevalence is **~1.2%** (624 fraud events out of 50,000 total).

### Why Accuracy is a Deceptive Metric
A trivial dummy model that always predicts `0` (Legitimate) would achieve **98.8% Accuracy**, yet fail to detect a single fraudulent transaction ($\text{Recall} = 0\%$), resulting in catastrophic financial losses.

Therefore, Aegis evaluates models using:
1. **Precision-Recall AUC (PR-AUC)**: The primary metric for severe imbalance.
2. **ROC-AUC**: Evaluates overall discrimination ability across all thresholds.
3. **Recall (Sensitivity)**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$ — percentage of actual fraudulent transactions intercepted.
4. **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$ — proportion of alerts that are genuine fraud (minimizing false positives and operational cost).
5. **F1-Score**: Harmonic mean of Precision and Recall.
6. **Precision@K**: The precision among the top $K$ highest-risk flagged transactions.

---

## 2. Chronological Train / Validation / Test Splitting

Standard random $k$-fold cross-validation or `train_test_split(shuffle=True)` is **invalid** for financial fraud modeling because it leaks future spending patterns and merchant distributions into historical training splits.

Aegis enforces a strict **temporal split**:

```
[------------- 70% Training -------------] [--- 15% Val ---] [--- 15% Test ---]
Oldest Events -------------------------------------------------> Newest Events
```

- **Training Set (35,000 rows)**: $T_0 \to T_{35000}$ — used for gradient boosting updates.
- **Validation Set (7,500 rows)**: $T_{35000} \to T_{42500}$ — used for early stopping and threshold tuning.
- **Held-Out Test Set (7,500 rows)**: $T_{42500} \to T_{50000}$ — strictly held out for final empirical evaluation.

---

## 3. The 16 Engineered Features

To eliminate training/serving skew, Aegis shares a unified feature extractor (`ml/training/feature_engineering.py`) between offline batch training and real-time streaming inference:

| Feature Name | Type | Mathematical / Logical Definition | Fraud Indicator |
| :--- | :--- | :--- | :--- |
| `transaction_count_1m` | int | Count of transactions from account in last 60 seconds | Automated card testing / bot attacks |
| `transaction_count_5m` | int | Count of transactions from account in last 300 seconds | High-velocity card draining |
| `transaction_amount_sum_5m`| float| Sum of amounts spent by account in last 5 minutes | Rapid balance depletion |
| `transaction_amount_avg_5m`| float| Mean transaction amount in last 5 minutes | Account takeover spike |
| `transaction_amount_std_5m`| float| Sample standard deviation of amounts in 5m window | Inconsistent spending behavior |
| `amount_z_score` | float| $Z = \frac{\text{amount} - \mu_{5m}}{\sigma_{5m}}$ | Extreme positive deviation from normal spend |
| `unique_merchants_10m` | int | Distinct merchant IDs transacted with in last 10m | Multi-merchant spray attacks |
| `unique_countries_30m` | int | Distinct country codes recorded in last 30m | Distributed credential compromise |
| `unique_devices_30m` | int | Distinct device fingerprints observed in last 30m | Device spoofing / emulator farm |
| `international_transaction_count` | int | Count of foreign transactions within 30m | Overseas cashouts |
| `time_since_previous_transaction` | float| Seconds elapsed since previous transaction | Bursts (< 5 seconds) |
| `distance_from_previous_transaction` | float| Haversine distance ($km$) from last transaction location | Geolocation spoofing |
| `device_change_flag` | binary| 1 if current `device_id` differs from account history | New hardware login |
| `country_change_flag` | binary| 1 if current `country` differs from previous event | Foreign IP proxy |
| `velocity_score` | float| Continuous composite velocity metric: $\frac{\text{txn\_count\_5m} \times 10}{\max(\Delta t, 1)}$ | Carding attack burst |
| `merchant_risk_score` | float| Risk weight assigned to category (e.g., Crypto=0.9, Luxury=0.7) | High-risk cashout merchants |

---

## 4. Addressing Imbalance: Model Comparison

During the ML training pipeline (`ml/training/train.py`), Aegis trains and compares three model configurations:

1. **Baseline Model**: Standard XGBoost with uniform sample weighting.
2. **Class-Weighted Model**: XGBoost with `scale_pos_weight`:
   $$\text{scale\_pos\_weight} = \frac{N_{\text{negative}}}{N_{\text{positive}}} = \frac{34575}{425} \approx 81.35$$
   This penalizes false negatives $81\times$ more heavily than false positives, forcing the boosting trees to split on rare fraud indicators.
3. **Resampled Model (SMOTE-style)**: Synthetic minority oversampling applied to training folds.

### Why Class-Weighted XGBoost is Chosen for Aegis
Empirical experiments confirm that `scale_pos_weight` achieves optimal PR-AUC without introducing synthetic interpolation artifacts into sparse discrete binary flags (`device_change_flag`, `country_change_flag`), preserving clean probability calibrations.

---

## 5. Threshold Optimization

Instead of blindly relying on the default binary classification threshold of $\tau = 0.5$, Aegis scans the validation set across thresholds from $0.05$ to $0.95$ in increments of $0.05$:

```python
best_threshold = 0.5
best_f1 = 0.0
for thresh in np.arange(0.05, 0.95, 0.05):
    f1 = f1_score(y_val, (y_val_prob >= thresh).astype(int))
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = thresh
```

- **Optimal Selected Threshold**: $\tau = 0.85$
- **Low Risk**: $P(\text{fraud}) < 0.30$
- **Medium Risk**: $0.30 \le P(\text{fraud}) < 0.85$
- **High Risk / Fraud Alert**: $P(\text{fraud}) \ge 0.85$

---

## 6. Real-Time Explainability & Reason Codes

Aegis pairs XGBoost probability predictions with a deterministic reason-code engine to produce human-auditable explanations for compliance and fraud triage:

```python
REASON_RULES = [
    ("IMPOSSIBLE_TRAVEL", lambda f: f.geo_velocity_kmh > 800.0 or f.distance_from_previous > 2000.0),
    ("UNUSUAL_AMOUNT", lambda f: f.amount_z_score > 3.0 or f.amount > 50000.0),
    ("HIGH_TRANSACTION_VELOCITY", lambda f: f.transaction_count_1m >= 5 or f.velocity_score > 15.0),
    ("NEW_DEVICE", lambda f: f.device_change_flag == 1),
    ("NEW_COUNTRY", lambda f: f.country_change_flag == 1),
    ("UNUSUAL_MERCHANT", lambda f: f.merchant_risk_score >= 0.70),
    ("INTERNATIONAL_SPIKE", lambda f: f.international_transaction_count >= 2),
    ("MULTIPLE_TRANSACTIONS", lambda f: f.transaction_count_5m >= 8),
]
```

This guarantees that every flagged alert provides fraud analysts with exact root causes without black-box opacity.
