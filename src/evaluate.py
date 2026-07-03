"""
evaluate.py — Custom evaluation metrics for SBA loan charge-off prediction.

Metrics:
- PR-AUC (Average Precision) — primary metric for imbalanced classification
- ROC-AUC — secondary, for literature comparison
- F1 at optimal threshold
- Precision @ top K% — "of the riskiest K% we flag, how many actually charge off?"
- Expected Loss accuracy — predicted EL vs actual charge-off amounts
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    f1_score,
    precision_recall_curve,
    classification_report,
    confusion_matrix,
)


def compute_pr_auc(y_true, y_prob):
    """Compute PR-AUC (Average Precision Score)."""
    return average_precision_score(y_true, y_prob)


def compute_roc_auc(y_true, y_prob):
    """Compute ROC-AUC."""
    return roc_auc_score(y_true, y_prob)


def optimal_f1_threshold(y_true, y_prob):
    """
    Find the probability threshold that maximizes F1 score.
    
    Returns
    -------
    tuple (best_threshold, best_f1)
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    
    # Compute F1 for each threshold
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_scores)
    
    # precision_recall_curve returns n+1 precision/recall values but n thresholds
    best_threshold = thresholds[min(best_idx, len(thresholds) - 1)]
    best_f1 = f1_scores[best_idx]
    
    return best_threshold, best_f1


def precision_at_top_k(y_true, y_prob, k_pct: float = 0.10):
    """
    Compute precision at top K% — of the riskiest K% of loans we flag,
    what fraction actually charged off?
    
    Parameters
    ----------
    k_pct : float
        Fraction of loans to flag (e.g., 0.10 = top 10%)
    """
    n_flag = max(int(len(y_true) * k_pct), 1)
    top_indices = np.argsort(y_prob)[::-1][:n_flag]
    precision = y_true.iloc[top_indices].mean() if hasattr(y_true, 'iloc') else y_true[top_indices].mean()
    return precision


def expected_loss_accuracy(y_true_loss, predicted_el):
    """
    Compare predicted expected loss vs actual charge-off amounts.
    
    Returns
    -------
    dict with MAE, RMSE, and total portfolio EL comparison.
    """
    actual = np.array(y_true_loss)
    predicted = np.array(predicted_el)
    
    mae = np.mean(np.abs(actual - predicted))
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    total_actual = actual.sum()
    total_predicted = predicted.sum()
    
    return {
        'mae': mae,
        'rmse': rmse,
        'total_actual_loss': total_actual,
        'total_predicted_el': total_predicted,
        'portfolio_error_pct': abs(total_predicted - total_actual) / max(total_actual, 1) * 100,
    }


def full_evaluation_report(y_true, y_prob, y_true_loss=None, predicted_el=None, k_pct=0.10):
    """
    Run the complete evaluation suite and return a summary dict.
    
    Parameters
    ----------
    y_true : array-like
        Binary true labels (0/1).
    y_prob : array-like
        Predicted probabilities of the positive class.
    y_true_loss : array-like, optional
        Actual dollar losses (ChgOffPrinGr for defaults, 0 for non-defaults).
    predicted_el : array-like, optional
        Predicted expected loss per loan.
    k_pct : float
        Top K% for precision@K.
    
    Returns
    -------
    dict
    """
    best_threshold, best_f1 = optimal_f1_threshold(y_true, y_prob)
    y_pred = (y_prob >= best_threshold).astype(int)
    
    results = {
        'pr_auc': compute_pr_auc(y_true, y_prob),
        'roc_auc': compute_roc_auc(y_true, y_prob),
        'best_f1': best_f1,
        'best_threshold': best_threshold,
        f'precision_at_top_{int(k_pct*100)}pct': precision_at_top_k(y_true, y_prob, k_pct),
    }
    
    if y_true_loss is not None and predicted_el is not None:
        results['expected_loss'] = expected_loss_accuracy(y_true_loss, predicted_el)
    
    # Print summary
    print("\n" + "=" * 50)
    print("MODEL EVALUATION REPORT")
    print("=" * 50)
    for k, v in results.items():
        if isinstance(v, dict):
            print(f"\n  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv:,.2f}")
        else:
            print(f"  {k}: {v:.4f}")
    print("=" * 50)
    
    print(f"\nClassification Report (threshold={best_threshold:.3f}):")
    print(classification_report(y_true, y_pred, target_names=['PIF', 'CHGOFF']))
    
    return results
