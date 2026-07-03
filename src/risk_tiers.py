"""
risk_tiers.py — Map predicted PD scores to actionable risk tiers.

Risk Tier System:
  Tier 1 (Green)  — PD < 10%   → Auto-approve
  Tier 2 (Yellow) — PD 10-25%  → Manual review required
  Tier 3 (Orange) — PD 25-40%  → Senior review + additional collateral
  Tier 4 (Red)    — PD > 40%   → Recommend denial
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
RISK_TIERS = {
    1: {'label': 'TIER 1 — AUTO-APPROVE',     'color': 'green',  'emoji': '🟢', 'pd_min': 0.00, 'pd_max': 0.10},
    2: {'label': 'TIER 2 — MANUAL REVIEW',     'color': 'yellow', 'emoji': '🟡', 'pd_min': 0.10, 'pd_max': 0.25},
    3: {'label': 'TIER 3 — SENIOR REVIEW',     'color': 'orange', 'emoji': '🟠', 'pd_min': 0.25, 'pd_max': 0.40},
    4: {'label': 'TIER 4 — RECOMMEND DENIAL',  'color': 'red',    'emoji': '🔴', 'pd_min': 0.40, 'pd_max': 1.00},
}


def assign_risk_tier(pd_score: float) -> int:
    """Assign a single PD score to its risk tier (1-4)."""
    if pd_score < 0.10:
        return 1
    elif pd_score < 0.25:
        return 2
    elif pd_score < 0.40:
        return 3
    else:
        return 4


def assign_risk_tiers(pd_scores: np.ndarray) -> np.ndarray:
    """Vectorized risk tier assignment for an array of PD scores."""
    tiers = np.ones_like(pd_scores, dtype=int)
    tiers[pd_scores >= 0.10] = 2
    tiers[pd_scores >= 0.25] = 3
    tiers[pd_scores >= 0.40] = 4
    return tiers


def get_tier_info(tier: int) -> dict:
    """Get the display info for a given tier number."""
    return RISK_TIERS.get(tier, RISK_TIERS[4])


def format_risk_assessment(pd_score: float, expected_loss: float, bank_exposure: float, sba_covers: float) -> dict:
    """
    Format a complete risk assessment for display (e.g., in Streamlit).
    
    Returns
    -------
    dict with formatted risk assessment details.
    """
    tier = assign_risk_tier(pd_score)
    info = get_tier_info(tier)
    
    return {
        'tier': tier,
        'tier_label': info['label'],
        'tier_emoji': info['emoji'],
        'tier_color': info['color'],
        'default_probability': f"{pd_score:.1%}",
        'expected_loss': f"${expected_loss:,.0f}",
        'bank_exposure': f"${bank_exposure:,.0f}",
        'sba_covers': f"${sba_covers:,.0f}",
    }


def tier_distribution_summary(pd_scores: np.ndarray) -> pd.DataFrame:
    """
    Summarize the distribution of loans across risk tiers.
    Useful for portfolio-level analytics.
    """
    tiers = assign_risk_tiers(pd_scores)
    
    rows = []
    for t in [1, 2, 3, 4]:
        mask = tiers == t
        info = RISK_TIERS[t]
        rows.append({
            'Tier': f"{info['emoji']} {info['label']}",
            'Count': mask.sum(),
            'Pct': f"{mask.mean():.1%}",
            'Avg PD': f"{pd_scores[mask].mean():.1%}" if mask.any() else 'N/A',
        })
    
    return pd.DataFrame(rows)
