# Fraud Risk Decision Engine Architecture

This document details the multi-factor risk scoring pipeline combining machine learning inferences, deterministic business rules, behavioral profiles, and threshold-based decision policies.

```mermaid
flowchart TD
    subgraph TXN_INPUT["Transaction Ingestion"]
        TXN["Incoming Transaction Payload"]
    end

    subgraph DUAL_EVALUATION["Dual Evaluation Pipelines"]
        subgraph ML_BRANCH["Machine Learning Pipeline"]
            VEC["20-Feature Vector"]
            XGB["XGBoost In-Memory Model"]
            P_ML["ML Probability (0.0 to 1.0)"]
            VEC --> XGB --> P_ML
        end

        subgraph RULE_BRANCH["Deterministic Rule Engine"]
            R1["R1: HIGH_TRANSACTION_VELOCITY (>5 in 1m)"]
            R2["R2: UNUSUAL_AMOUNT (>3x mean or >5k)"]
            R3["R3: IMPOSSIBLE_TRAVEL (>800 km/h)"]
            R4["R4: NEW_DEVICE (unseen hardware fingerprint)"]
            R5["R5: NEW_COUNTRY (unseen ISO location)"]
            R6["R6: UNUSUAL_MERCHANT (unseen high-risk merchant)"]
            R7["R7: INTERNATIONAL_SPIKE (amount > $1,000 abroad)"]
            R8["R8: MULTIPLE_RAPID_TXNS (>3 in 10s)"]
            
            RULES_EXEC["Evaluate 8 Rules Against Profiles"]
            R1 --> RULES_EXEC
            R2 --> RULES_EXEC
            R3 --> RULES_EXEC
            R4 --> RULES_EXEC
            R5 --> RULES_EXEC
            R6 --> RULES_EXEC
            R7 --> RULES_EXEC
            R8 --> RULES_EXEC
            
            VIOLATIONS["Structured Rule Violations & Weights"]
            RULES_EXEC --> VIOLATIONS
        end

        subgraph PROFILES["Entity Behavioral Profiling"]
            CUST["Customer Profile (Normal spend mean, std, max)"]
            MERCH["Merchant Profile (Chargeback rate, risk factor)"]
        end
    end

    subgraph ARBITRATION["Multi-Factor Decision Engine"]
        FORMULA["Calibrated Risk Score Calculation:
        Risk Score = 0.50 * (P_ML * 100) + 0.30 * (Rule Penalty) + 0.10 * Customer Risk + 0.10 * Merchant Risk"]
        
        CRITICAL_CHECK{"Hard Kill Triggered?
        (Impossible Travel OR Velocity > 8 OR Amount > 10x Max)"}
    end

    subgraph POLICY["Decision Thresholds"]
        DEC_APPROVE["APPROVE
        (Risk Score: 0 - 30)
        Low Risk: Instant Settlement"]
        
        DEC_REVIEW["REVIEW
        (Risk Score: 31 - 70)
        Medium/High Risk: 2FA / SOC Analyst Queue"]
        
        DEC_DECLINE["DECLINE
        (Risk Score: 71 - 100)
        Critical Risk: Hard Block & Account Flag"]
    end

    TXN --> ML_BRANCH
    TXN --> RULE_BRANCH
    TXN --> PROFILES
    
    P_ML --> FORMULA
    VIOLATIONS --> FORMULA
    CUST --> FORMULA
    MERCH --> FORMULA
    
    FORMULA --> CRITICAL_CHECK
    CRITICAL_CHECK -->|"Yes (Immediate 95+)"| DEC_DECLINE
    CRITICAL_CHECK -->|"No"| SCORE_EVAL["Evaluate Calibrated Score"]
    
    SCORE_EVAL -->|"0 <= Score <= 30"| DEC_APPROVE
    SCORE_EVAL -->|"31 <= Score <= 70"| DEC_REVIEW
    SCORE_EVAL -->|"71 <= Score <= 100"| DEC_DECLINE
```

## Risk Score Calibration Formulas
The composite risk score $S \in [0, 100]$ is computed as:
$$S = \text{clamp}\left(0.50 \cdot (p_{\text{fraud}} \times 100) + 0.30 \cdot W_{\text{rules}} + 0.10 \cdot S_{\text{customer}} + 0.10 \cdot S_{\text{merchant}} + \Delta_{\text{spend}}, 0, 100\right)$$

Where:
- $p_{\text{fraud}}$: Raw probability predicted by XGBoost model.
- $W_{\text{rules}}$: Sum of severity-weighted rule violations (Critical: 35, High: 20, Medium: 10, Low: 5), capped at 100.
- $S_{\text{customer}}$: Customer risk score based on historical chargeback or dispute history.
- $S_{\text{merchant}}$: Merchant risk score derived from historical fraud-to-transaction ratio.
- $\Delta_{\text{spend}}$: Extra penalty if current transaction exceeds 3 standard deviations from normal spend.

