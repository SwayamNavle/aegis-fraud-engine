#!/usr/bin/env python3
"""
Aegis Machine Learning Training Pipeline
=========================================
Trains and evaluates XGBoost fraud detection classifiers on imbalanced streaming data.
Compares:
1. Baseline Model (unweighted)
2. Class-Weighted Model (scale_pos_weight = N_neg / N_pos)
3. Balanced Re-sampled Model (SMOTE-style minority augmentation)

Chronological train / validation / test splits are strictly maintained to prevent future data leakage.
Outputs serialized model, metrics, and metadata artifacts.
"""

import json
import os
import sys
import time
import yaml
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime, timezone
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.training.feature_engineering import engineer_features_batch, FEATURE_NAMES
from ml.training.evaluate import evaluate_model, find_optimal_threshold
from scripts.generate_demo_data import generate_dataset


def load_or_generate_dataset(csv_path: str, count: int = 25000, fraud_ratio: float = 0.018) -> pd.DataFrame:
    """Loads transaction dataset or generates synthetic data if missing."""
    if os.path.exists(csv_path):
        print(f"[Aegis Train] Loading dataset from: {csv_path}")
        df = pd.read_csv(csv_path)
    else:
        print(f"[Aegis Train] Dataset not found at {csv_path}. Generating synthetic dataset...")
        df = generate_dataset(num_records=count, fraud_ratio=fraud_ratio, output_csv=csv_path)
    return df


def chronological_split(X: pd.DataFrame, y: pd.Series,
                        train_ratio: float = 0.70,
                        val_ratio: float = 0.15) -> Tuple:
    """Splits data strictly chronologically into train, validation, and test sets."""
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
    X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
    X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

    print(f"[Aegis Split] Chronological Split: Train={len(X_train):,} | Val={len(X_val):,} | Test={len(X_test):,}")
    print(f"[Aegis Split] Train fraud count: {y_train.sum():,} ({y_train.mean()*100:.2f}%)")
    print(f"[Aegis Split] Val fraud count:   {y_val.sum():,} ({y_val.mean()*100:.2f}%)")
    print(f"[Aegis Split] Test fraud count:  {y_test.sum():,} ({y_test.mean()*100:.2f}%)")
    return X_train, y_train, X_val, y_val, X_test, y_test


def resample_balanced(X: pd.DataFrame, y: pd.Series, target_ratio: float = 0.20) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Minority augmentation / synthetic interpolation for imbalanced data.
    Boosts fraud representation to target_ratio to train balanced variant.
    """
    fraud_mask = (y == 1)
    X_fraud = X[fraud_mask].values
    X_legit = X[~fraud_mask].values

    n_fraud = len(X_fraud)
    n_legit = len(X_legit)
    target_fraud_n = int(n_legit * target_ratio)

    if n_fraud < 2 or target_fraud_n <= n_fraud:
        return X, y

    # Generate synthetic minority samples via random convex combinations of nearest pairs
    additional_needed = target_fraud_n - n_fraud
    synthetic_samples = []
    for _ in range(additional_needed):
        idx1, idx2 = np.random.choice(n_fraud, size=2, replace=True)
        alpha = np.random.uniform(0.1, 0.9)
        syn = alpha * X_fraud[idx1] + (1 - alpha) * X_fraud[idx2]
        # Jitter slightly
        syn += np.random.normal(0, 0.02, size=syn.shape)
        synthetic_samples.append(syn)

    X_augmented = np.vstack([X_legit, X_fraud, np.array(synthetic_samples)])
    y_augmented = np.array([0] * n_legit + [1] * (n_fraud + additional_needed))

    return pd.DataFrame(X_augmented, columns=X.columns), pd.Series(y_augmented)


def train_pipeline(config_path: str = "ml/training/model_config.yaml") -> Dict[str, Any]:
    print("=" * 70)
    print("   AEGIS XGBOOST FRAUD DETECTION MODEL TRAINING PIPELINE   ")
    print("=" * 70)

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # 1. Load / Generate Data
    df = load_or_generate_dataset(
        cfg["data"]["raw_path"],
        count=30000,
        fraud_ratio=cfg["data"]["fraud_ratio"]
    )

    # 2. Extract Features
    X, y = engineer_features_batch(df)

    # 3. Chronological Split
    X_train, y_train, X_val, y_val, X_test, y_test = chronological_split(
        X, y,
        train_ratio=cfg["data"]["train_split"],
        val_ratio=cfg["data"]["val_split"]
    )

    # Calculate class imbalance weighting factor
    num_neg = int((y_train == 0).sum())
    num_pos = max(1, int((y_train == 1).sum()))
    scale_pos_weight = float(num_neg / num_pos)
    print(f"[Aegis Train] Negative: {num_neg:,} | Positive: {num_pos:,} | scale_pos_weight: {scale_pos_weight:.2f}")

    models = {}
    val_metrics = {}
    benchmarks = {}

    # -----------------------------------------------------------------
    # BASELINE 1: LOGISTIC REGRESSION (Linear Baseline)
    # -----------------------------------------------------------------
    print("\n--- Training Baseline 1: Logistic Regression ---")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    lr_model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    t0 = time.perf_counter()
    lr_model.fit(X_train_scaled, y_train)
    lr_fit_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    lr_val_probs = lr_model.predict_proba(X_val_scaled)[:, 1]
    lr_inf_latency_ms = ((time.perf_counter() - t0) / len(X_val)) * 1000.0

    lr_val_eval = evaluate_model(y_val.values, lr_val_probs, threshold=0.5)
    print(f"  Logistic Regression Val PR-AUC: {lr_val_eval['pr_auc']:.4f} | F1: {lr_val_eval['f1_score']:.4f} | Latency: {lr_inf_latency_ms:.4f}ms/txn")
    benchmarks["logistic_regression"] = {
        "pr_auc": lr_val_eval["pr_auc"],
        "roc_auc": lr_val_eval["roc_auc"],
        "f1_score": lr_val_eval["f1_score"],
        "precision": lr_val_eval["precision"],
        "recall": lr_val_eval["recall"],
        "fit_time_sec": round(lr_fit_time, 3),
        "inf_latency_ms": round(lr_inf_latency_ms, 4)
    }

    # -----------------------------------------------------------------
    # BASELINE 2: RANDOM FOREST (Bagging Ensemble)
    # -----------------------------------------------------------------
    print("\n--- Training Baseline 2: Random Forest ---")
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1)
    t0 = time.perf_counter()
    rf_model.fit(X_train, y_train)
    rf_fit_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    rf_val_probs = rf_model.predict_proba(X_val)[:, 1]
    rf_inf_latency_ms = ((time.perf_counter() - t0) / len(X_val)) * 1000.0

    rf_val_eval = evaluate_model(y_val.values, rf_val_probs, threshold=0.5)
    print(f"  Random Forest Val PR-AUC: {rf_val_eval['pr_auc']:.4f} | F1: {rf_val_eval['f1_score']:.4f} | Latency: {rf_inf_latency_ms:.4f}ms/txn")
    benchmarks["random_forest"] = {
        "pr_auc": rf_val_eval["pr_auc"],
        "roc_auc": rf_val_eval["roc_auc"],
        "f1_score": rf_val_eval["f1_score"],
        "precision": rf_val_eval["precision"],
        "recall": rf_val_eval["recall"],
        "fit_time_sec": round(rf_fit_time, 3),
        "inf_latency_ms": round(rf_inf_latency_ms, 4)
    }

    # -----------------------------------------------------------------
    # MODEL 1: BASELINE XGBoost (Unweighted Gradient Boosting)
    # -----------------------------------------------------------------
    print("\n--- Training Model 3: XGBoost Baseline (Unweighted) ---")
    t0 = time.perf_counter()
    base_model = XGBClassifier(
        n_estimators=cfg["model"]["n_estimators"],
        max_depth=cfg["model"]["max_depth"],
        learning_rate=cfg["model"]["learning_rate"],
        subsample=cfg["model"]["subsample"],
        colsample_bytree=cfg["model"]["colsample_bytree"],
        random_state=cfg["model"]["random_state"],
        eval_metric=cfg["model"]["eval_metric"]
    )
    base_model.fit(X_train, y_train)
    xgb_fit_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    base_val_probs = base_model.predict_proba(X_val)[:, 1]
    xgb_inf_latency_ms = ((time.perf_counter() - t0) / len(X_val)) * 1000.0

    models["baseline"] = base_model
    val_metrics["baseline"] = evaluate_model(y_val.values, base_val_probs, threshold=0.5)
    print(f"  XGBoost Baseline Val PR-AUC: {val_metrics['baseline']['pr_auc']:.4f} | F1: {val_metrics['baseline']['f1_score']:.4f} | Latency: {xgb_inf_latency_ms:.4f}ms/txn")
    benchmarks["xgboost_baseline"] = {
        "pr_auc": val_metrics["baseline"]["pr_auc"],
        "roc_auc": val_metrics["baseline"]["roc_auc"],
        "f1_score": val_metrics["baseline"]["f1_score"],
        "precision": val_metrics["baseline"]["precision"],
        "recall": val_metrics["baseline"]["recall"],
        "fit_time_sec": round(xgb_fit_time, 3),
        "inf_latency_ms": round(xgb_inf_latency_ms, 4)
    }

    # -----------------------------------------------------------------
    # MODEL 2: CLASS-WEIGHTED XGBoost (scale_pos_weight)
    # -----------------------------------------------------------------
    print("\n--- Training Model 4: Class-Weighted XGBoost (scale_pos_weight) ---")
    weighted_model = XGBClassifier(
        n_estimators=cfg["model"]["n_estimators"],
        max_depth=cfg["model"]["max_depth"],
        learning_rate=cfg["model"]["learning_rate"],
        subsample=cfg["model"]["subsample"],
        colsample_bytree=cfg["model"]["colsample_bytree"],
        scale_pos_weight=scale_pos_weight,
        random_state=cfg["model"]["random_state"],
        eval_metric=cfg["model"]["eval_metric"]
    )
    weighted_model.fit(X_train, y_train)
    weighted_val_probs = weighted_model.predict_proba(X_val)[:, 1]
    models["class_weighted"] = weighted_model
    val_metrics["class_weighted"] = evaluate_model(y_val.values, weighted_val_probs, threshold=0.5)
    print(f"  Class-Weighted Val PR-AUC: {val_metrics['class_weighted']['pr_auc']:.4f} | F1: {val_metrics['class_weighted']['f1_score']:.4f}")

    # -----------------------------------------------------------------
    # MODEL 3: BALANCED RESAMPLED XGBoost (Synthetic Augmentation)
    # -----------------------------------------------------------------
    print("\n--- Training Model 5: Balanced Resampled XGBoost (SMOTE-style) ---")
    X_train_res, y_train_res = resample_balanced(X_train, y_train, target_ratio=0.25)
    smote_model = XGBClassifier(
        n_estimators=cfg["model"]["n_estimators"],
        max_depth=cfg["model"]["max_depth"],
        learning_rate=cfg["model"]["learning_rate"],
        subsample=cfg["model"]["subsample"],
        colsample_bytree=cfg["model"]["colsample_bytree"],
        random_state=cfg["model"]["random_state"],
        eval_metric=cfg["model"]["eval_metric"]
    )
    smote_model.fit(X_train_res, y_train_res)
    smote_val_probs = smote_model.predict_proba(X_val)[:, 1]
    models["resampled"] = smote_model
    val_metrics["resampled"] = evaluate_model(y_val.values, smote_val_probs, threshold=0.5)
    print(f"  Resampled Val PR-AUC: {val_metrics['resampled']['pr_auc']:.4f} | F1: {val_metrics['resampled']['f1_score']:.4f}")

    # -----------------------------------------------------------------
    # CHAMPION SELECTION (Highest PR-AUC on Validation Set)
    # -----------------------------------------------------------------
    champion_name = max(val_metrics, key=lambda k: (val_metrics[k]["pr_auc"], val_metrics[k]["f1_score"]))
    champion_model = models[champion_name]
    print(f"\n[Aegis Champion] Selected Champion Architecture: '{champion_name.upper()}'")

    # -----------------------------------------------------------------
    # THRESHOLD OPTIMIZATION
    # -----------------------------------------------------------------
    champion_val_probs = champion_model.predict_proba(X_val)[:, 1]
    optimal_threshold, opt_metrics = find_optimal_threshold(y_val.values, champion_val_probs)
    print(f"[Aegis Threshold] Optimal Decision Threshold: {optimal_threshold:.4f} (Max F1={opt_metrics['f1']:.4f})")

    # -----------------------------------------------------------------
    # FINAL HELD-OUT TEST EVALUATION
    # -----------------------------------------------------------------
    print("\n--- Evaluating Champion Model on Held-Out Test Set ---")
    test_probs = champion_model.predict_proba(X_test)[:, 1]
    test_eval_default = evaluate_model(y_test.values, test_probs, threshold=0.5)
    test_eval_optimal = evaluate_model(y_test.values, test_probs, threshold=optimal_threshold)

    print(f"  Test PR-AUC:                  {test_eval_optimal['pr_auc']:.4f}")
    print(f"  Test ROC-AUC:                 {test_eval_optimal['roc_auc']:.4f}")
    print(f"  Test Precision (at {optimal_threshold:.2f}):   {test_eval_optimal['precision']:.4f}")
    print(f"  Test Recall (at {optimal_threshold:.2f}):      {test_eval_optimal['recall']:.4f}")
    print(f"  Test F1-Score (at {optimal_threshold:.2f}):    {test_eval_optimal['f1_score']:.4f}")
    print(f"  Test Precision@50:            {test_eval_optimal['precision_at_50']:.4f}")
    print(f"  Confusion Matrix:             {test_eval_optimal['confusion_matrix']}")

    # -----------------------------------------------------------------
    # PERSIST ARTIFACTS
    # -----------------------------------------------------------------
    os.makedirs(cfg["artifacts"]["model_dir"], exist_ok=True)
    os.makedirs(cfg["artifacts"]["artifacts_dir"], exist_ok=True)

    # 1. Save Model JSON
    model_save_path = os.path.join(cfg["artifacts"]["model_dir"], cfg["artifacts"]["model_filename"])
    champion_model.save_model(model_save_path)
    print(f"[Aegis Artifacts] Model saved to: {model_save_path}")

    # 2. Save Feature Schema
    schema_path = os.path.join(cfg["artifacts"]["artifacts_dir"], cfg["artifacts"]["schema_filename"])
    with open(schema_path, "w") as f:
        json.dump({
            "features": FEATURE_NAMES,
            "feature_count": len(FEATURE_NAMES),
            "model_version": cfg["model"]["version"]
        }, f, indent=2)

    # 3. Save Feature Importance
    importance_scores = champion_model.feature_importances_
    feat_imp = {
        name: round(float(score), 5)
        for name, score in sorted(zip(FEATURE_NAMES, importance_scores), key=lambda x: x[1], reverse=True)
    }
    importance_path = os.path.join(cfg["artifacts"]["artifacts_dir"], cfg["artifacts"]["feature_importance_filename"])
    with open(importance_path, "w") as f:
        json.dump(feat_imp, f, indent=2)

    # 4. Save Confusion Matrix
    cm_path = os.path.join(cfg["artifacts"]["artifacts_dir"], cfg["artifacts"]["confusion_matrix_filename"])
    with open(cm_path, "w") as f:
        json.dump(test_eval_optimal["confusion_matrix"], f, indent=2)

    # 5. Save Complete Metrics JSON
    metrics_path = os.path.join(cfg["artifacts"]["artifacts_dir"], cfg["artifacts"]["metrics_filename"])
    final_metrics = {
        "model_version": cfg["model"]["version"],
        "champion_architecture": champion_name,
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "optimal_threshold": optimal_threshold,
        "test_metrics": test_eval_optimal,
        "test_metrics_default_threshold": test_eval_default,
        "model_comparison_val": val_metrics
    }
    with open(metrics_path, "w") as f:
        json.dump(final_metrics, f, indent=2)

    # 6. Save Training Metadata
    metadata_path = os.path.join(cfg["artifacts"]["artifacts_dir"], cfg["artifacts"]["metadata_filename"])
    metadata = {
        "model_name": cfg["model"]["name"],
        "model_version": cfg["model"]["version"],
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": len(df),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
        "scale_pos_weight": round(scale_pos_weight, 2),
        "optimal_threshold": round(optimal_threshold, 4),
        "features": FEATURE_NAMES,
        "champion_model": champion_name
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # 7. Save Baseline Multi-Model Comparison (Logistic Regression vs Random Forest vs XGBoost)
    baseline_path = os.path.join(cfg["artifacts"]["artifacts_dir"], "baseline_comparison.json")
    with open(baseline_path, "w") as f:
        json.dump(benchmarks, f, indent=2)
    print(f"[Aegis Artifacts] Baseline comparison saved to: {baseline_path}")

    print(f"[Aegis Artifacts] All training artifacts successfully written to '{cfg['artifacts']['artifacts_dir']}'")
    return final_metrics


if __name__ == "__main__":
    train_pipeline()
