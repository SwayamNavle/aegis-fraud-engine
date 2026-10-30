"""
Aegis Model Evaluation Suite
Calculates rigorous metrics for extreme class imbalance:
- Precision, Recall, F1-Score
- ROC-AUC and PR-AUC (Average Precision)
- Confusion Matrix (TP, FP, TN, FN)
- False Positive Rate (FPR) and False Negative Rate (FNR)
- Precision@K for operational fraud investigation queues
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix, precision_recall_curve
)


def compute_precision_at_k(y_true: np.ndarray, y_probs: np.ndarray, k: int) -> float:
    """Calculates precision among top K highest risk scored transactions."""
    if len(y_true) == 0 or k <= 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_indices = np.argsort(y_probs)[::-1][:k]
    return float(np.mean(y_true[top_k_indices]))


def find_optimal_threshold(y_true: np.ndarray, y_probs: np.ndarray,
                           target_metric: str = "f1") -> Tuple[float, Dict[str, float]]:
    """
    Scans candidate decision thresholds to identify optimal operating point.
    Returns optimal threshold and associated performance metrics.
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_probs)
    f1_scores = (2 * precisions * recalls) / np.maximum(precisions + recalls, 1e-9)
    
    # Exclude boundary edge
    valid_len = len(thresholds)
    best_idx = np.argmax(f1_scores[:valid_len])
    best_threshold = float(thresholds[best_idx])
    
    # Cap threshold between 0.30 and 0.85 for production stability
    best_threshold = max(0.30, min(0.85, best_threshold))
    
    y_pred = (y_probs >= best_threshold).astype(int)
    metrics = {
        "optimal_threshold": round(best_threshold, 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4)
    }
    return best_threshold, metrics


def evaluate_model(y_true: np.ndarray, y_probs: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Comprehensive fraud evaluation suite.
    """
    y_pred = (y_probs >= threshold).astype(int)
    
    cm = confusion_matrix(y_true, y_pred)
    # cm layout: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()
    
    fpr = fp / max(1, fp + tn)
    fnr = fn / max(1, fn + tp)
    
    # PR-AUC is the true north-star metric for severe class imbalance
    pr_auc = float(average_precision_score(y_true, y_probs))
    try:
        roc_auc = float(roc_auc_score(y_true, y_probs))
    except Exception:
        roc_auc = 0.5
        
    p_at_50 = compute_precision_at_k(y_true, y_probs, 50)
    p_at_100 = compute_precision_at_k(y_true, y_probs, 100)

    return {
        "threshold_used": round(threshold, 4),
        "total_samples": int(len(y_true)),
        "actual_fraud_samples": int(np.sum(y_true)),
        "predicted_fraud_samples": int(np.sum(y_pred)),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "false_positive_rate": round(float(fpr), 4),
        "false_negative_rate": round(float(fnr), 4),
        "precision_at_50": round(p_at_50, 4),
        "precision_at_100": round(p_at_100, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }
