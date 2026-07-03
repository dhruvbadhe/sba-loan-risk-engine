"""
expected_loss.py — Expected Loss calculation using the Basel II/III framework.

EL = PD × LGD × EAD

Where:
- PD  = Probability of Default (from the classifier)
- LGD = Loss Given Default = (GrAppv - SBA_Appv) / GrAppv (unguaranteed %)
- EAD = Exposure at Default = GrAppv (total loan amount)
"""

import numpy as np
import pandas as pd


def compute_lgd(gr_appv: np.ndarray, sba_appv: np.ndarray) -> np.ndarray:
    """
    Compute Loss Given Default as the unguaranteed fraction.
    
    LGD = (GrAppv - SBA_Appv) / GrAppv
    
    The SBA guarantees a portion; the bank loses the rest on default.
    """
    gr_appv = np.array(gr_appv, dtype=float)
    sba_appv = np.array(sba_appv, dtype=float)
    
    lgd = np.where(
        gr_appv > 0,
        (gr_appv - sba_appv) / gr_appv,
        0.0
    )
    return np.clip(lgd, 0, 1)


def compute_expected_loss(
    pd_scores: np.ndarray,
    gr_appv: np.ndarray,
    sba_appv: np.ndarray,
) -> dict:
    """
    Compute Expected Loss for each loan.
    
    Parameters
    ----------
    pd_scores : array-like
        Predicted probability of default for each loan.
    gr_appv : array-like
        Gross approved loan amount (EAD).
    sba_appv : array-like
        SBA guaranteed amount.
    
    Returns
    -------
    dict with:
        - 'PD': array of default probabilities
        - 'LGD': array of loss given default
        - 'EAD': array of exposure at default
        - 'EL': array of expected loss per loan ($)
        - 'portfolio_EL': total portfolio expected loss
        - 'bank_exposure_if_default': dollar loss to bank per loan on default
        - 'sba_guarantee_covers': dollar amount SBA covers per loan
    """
    pd_scores = np.array(pd_scores, dtype=float)
    gr_appv = np.array(gr_appv, dtype=float)
    sba_appv = np.array(sba_appv, dtype=float)
    
    lgd = compute_lgd(gr_appv, sba_appv)
    ead = gr_appv
    el = pd_scores * lgd * ead
    
    return {
        'PD': pd_scores,
        'LGD': lgd,
        'EAD': ead,
        'EL': el,
        'portfolio_EL': el.sum(),
        'bank_exposure_if_default': lgd * ead,
        'sba_guarantee_covers': sba_appv,
    }


def compute_expected_loss_df(df: pd.DataFrame, pd_col: str = 'pd_score') -> pd.DataFrame:
    """
    Add expected loss columns to a DataFrame.
    
    Expects columns: GrAppv, SBA_Appv, and pd_col (predicted probability).
    """
    df = df.copy()
    
    result = compute_expected_loss(
        pd_scores=df[pd_col].values,
        gr_appv=df['GrAppv'].values,
        sba_appv=df['SBA_Appv'].values,
    )
    
    df['LGD'] = result['LGD']
    df['EAD'] = result['EAD']
    df['expected_loss'] = result['EL']
    df['bank_exposure'] = result['bank_exposure_if_default']
    df['sba_covers'] = result['sba_guarantee_covers']
    
    return df
