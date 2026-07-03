"""
features.py — Feature engineering for SBA loan charge-off prediction.

All features are computed in a LEAK-SAFE manner:
- Bank-level and industry-level aggregates use only loans approved BEFORE the current loan.
- Temporal features are derived from approval date without looking ahead.

Feature Categories:
1. Loan Structure Features
2. Borrower Profile Features
3. Industry Risk Features (NAICS)
4. Economic Cycle Features
5. Bank Quality Features (Leak-Safe)
6. Derived Risk Signals
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# NBER recession periods (start, end) — used for economic cycle features
# ---------------------------------------------------------------------------
RECESSION_PERIODS = [
    ('1990-07-01', '1991-03-31'),
    ('2001-03-01', '2001-11-30'),
    ('2007-12-01', '2009-06-30'),
]

# ---------------------------------------------------------------------------
# State-to-Census-Region mapping
# ---------------------------------------------------------------------------
STATE_TO_REGION = {
    'CT': 'Northeast', 'ME': 'Northeast', 'MA': 'Northeast', 'NH': 'Northeast',
    'RI': 'Northeast', 'VT': 'Northeast', 'NJ': 'Northeast', 'NY': 'Northeast',
    'PA': 'Northeast',
    'IL': 'Midwest', 'IN': 'Midwest', 'MI': 'Midwest', 'OH': 'Midwest',
    'WI': 'Midwest', 'IA': 'Midwest', 'KS': 'Midwest', 'MN': 'Midwest',
    'MO': 'Midwest', 'NE': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
    'DE': 'South', 'FL': 'South', 'GA': 'South', 'MD': 'South',
    'NC': 'South', 'SC': 'South', 'VA': 'South', 'DC': 'South',
    'WV': 'South', 'AL': 'South', 'KY': 'South', 'MS': 'South',
    'TN': 'South', 'AR': 'South', 'LA': 'South', 'OK': 'South', 'TX': 'South',
    'AZ': 'West', 'CO': 'West', 'ID': 'West', 'MT': 'West',
    'NV': 'West', 'NM': 'West', 'UT': 'West', 'WY': 'West',
    'AK': 'West', 'CA': 'West', 'HI': 'West', 'OR': 'West', 'WA': 'West',
}

HIGH_RISK_SECTORS = {'72', '44', '45', '81'}  # Food, Retail, Other Services


# ===========================================================================
# Category 1: Loan Structure Features
# ===========================================================================
def add_loan_structure_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add features derived from loan terms and structure."""
    df = df.copy()
    
    df['log_loan_amount'] = np.log1p(df['GrAppv'].fillna(0))
    df['sba_guarantee_ratio'] = (
        df['SBA_Appv'].fillna(0) / df['GrAppv'].replace(0, np.nan)
    ).clip(0, 1)
    df['term_months'] = df['Term'].fillna(0)
    df['loan_per_employee'] = (
        df['GrAppv'].fillna(0) / df['NoEmp'].clip(lower=1).fillna(1)
    )
    df['jobs_promised_ratio'] = (
        (df['CreateJob'].fillna(0) + df['RetainedJob'].fillna(0))
        / df['NoEmp'].clip(lower=1).fillna(1)
    )
    
    return df


# ===========================================================================
# Category 2: Borrower Profile Features
# ===========================================================================
def add_borrower_profile_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add features describing the borrower."""
    df = df.copy()
    
    # Franchise flag
    if 'FranchiseCode' in df.columns:
        fc = pd.to_numeric(df['FranchiseCode'], errors='coerce').fillna(0)
        df['is_franchise'] = ((fc != 0) & (fc != 1)).astype(int)
    
    # Urban/Rural
    if 'UrbanRural' in df.columns:
        ur = pd.to_numeric(df['UrbanRural'], errors='coerce').fillna(0)
        df['is_urban'] = (ur == 1).astype(int)
    
    # Employee count bins
    df['employee_bin'] = pd.cut(
        df['NoEmp'].fillna(0),
        bins=[-1, 5, 20, 100, float('inf')],
        labels=['1-5', '6-20', '21-100', '100+']
    )
    
    # State region
    if 'BorrState' in df.columns:
        df['state_region'] = df['BorrState'].str.strip().str.upper().map(STATE_TO_REGION)
    elif 'State' in df.columns:
        df['state_region'] = df['State'].str.strip().str.upper().map(STATE_TO_REGION)
    
    return df


# ===========================================================================
# Category 3: Industry Risk Features
# ===========================================================================
def add_industry_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add NAICS-based industry risk features.
    sector_historical_default_rate is computed leak-safe (expanding window).
    """
    df = df.copy()
    
    # High-risk industry flag
    df['is_high_risk_industry'] = df['naics_sector'].isin(HIGH_RISK_SECTORS).astype(int)
    
    # Leak-safe sector default rate (requires ApprovalDate sorted)
    if 'ApprovalDate' in df.columns and df['ApprovalDate'].notna().any():
        df = df.sort_values('ApprovalDate').reset_index(drop=True)
        df['sector_cumulative_defaults'] = df.groupby('naics_sector')['target'].cumsum() - df['target']
        df['sector_cumulative_count'] = df.groupby('naics_sector').cumcount()
        df['sector_historical_default_rate'] = (
            df['sector_cumulative_defaults'] / df['sector_cumulative_count'].clip(lower=1)
        )
        df.drop(columns=['sector_cumulative_defaults', 'sector_cumulative_count'], inplace=True)
    
    return df


# ===========================================================================
# Category 4: Economic Cycle Features
# ===========================================================================
def add_economic_cycle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add features capturing the macroeconomic context at loan origination."""
    df = df.copy()
    
    df['approval_year'] = df['ApprovalFY'] if 'ApprovalFY' in df.columns else np.nan
    
    # Recession origination flag
    if 'ApprovalDate' in df.columns:
        df['is_recession_origination'] = 0
        for start, end in RECESSION_PERIODS:
            mask = (df['ApprovalDate'] >= start) & (df['ApprovalDate'] <= end)
            df.loc[mask, 'is_recession_origination'] = 1
    
    # Pre-crisis flag (2005–2007)
    if 'ApprovalFY' in df.columns:
        df['is_pre_crisis'] = df['ApprovalFY'].between(2005, 2007).astype(int)
    
    # Decade
    if 'ApprovalFY' in df.columns:
        df['decade'] = (df['ApprovalFY'] // 10 * 10).astype('Int64')
    
    return df


# ===========================================================================
# Category 5: Bank Quality Features (Leak-Safe)
# ===========================================================================
def add_bank_quality_features(df: pd.DataFrame, bank_col: str = 'Bank') -> pd.DataFrame:
    """
    Compute bank underwriting quality features using ONLY prior loans (leak-safe).
    
    CRITICAL: These features use an expanding window — for each loan, only loans
    approved strictly BEFORE this one are used to compute the bank's track record.
    """
    df = df.copy()
    
    if bank_col not in df.columns:
        return df
    
    # Sort by approval date for temporal calculation
    if 'ApprovalDate' in df.columns:
        df = df.sort_values('ApprovalDate').reset_index(drop=True)
    
    # Bank prior default rate (expanding window, excluding current loan)
    df['bank_cumulative_defaults'] = df.groupby(bank_col)['target'].cumsum() - df['target']
    df['bank_cumulative_count'] = df.groupby(bank_col).cumcount()
    
    df['bank_prior_default_rate'] = (
        df['bank_cumulative_defaults'] / df['bank_cumulative_count'].clip(lower=1)
    )
    # First loan from a bank has no history → fill with global mean
    df.loc[df['bank_cumulative_count'] == 0, 'bank_prior_default_rate'] = np.nan
    
    df['bank_prior_loan_count'] = df['bank_cumulative_count']
    
    # Bank experience tier
    df['bank_experience_tier'] = pd.cut(
        df['bank_prior_loan_count'],
        bins=[-1, 10, 100, float('inf')],
        labels=['Low', 'Medium', 'High']
    )
    
    # Same-state lender flag
    borrower_state = df.get('BorrState', df.get('State', pd.Series(dtype=str)))
    bank_state = df.get('BankState', pd.Series(dtype=str))
    if borrower_state is not None and bank_state is not None:
        df['is_same_state_bank'] = (
            borrower_state.str.strip().str.upper() == bank_state.str.strip().str.upper()
        ).astype(int)
    
    # Cleanup intermediate columns
    df.drop(columns=['bank_cumulative_defaults', 'bank_cumulative_count'], inplace=True)
    
    return df


# ===========================================================================
# Category 6: Derived Risk Signals
# ===========================================================================
def add_derived_risk_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add composite risk signals combining multiple features."""
    df = df.copy()
    
    df['unguaranteed_exposure'] = df['GrAppv'].fillna(0) - df['SBA_Appv'].fillna(0)
    df['large_loan_flag'] = (df['GrAppv'].fillna(0) > 500_000).astype(int)
    df['high_term_flag'] = (df['Term'].fillna(0) > 240).astype(int)
    
    median_loan = df['GrAppv'].median()
    df['new_biz_large_loan'] = (
        (df.get('is_new_business', 0) == 1) & (df['GrAppv'].fillna(0) > median_loan)
    ).astype(int)
    
    return df


# ===========================================================================
# Master Feature Engineering Pipeline
# ===========================================================================
def build_feature_matrix(df: pd.DataFrame, bank_col: str = 'Bank') -> pd.DataFrame:
    """
    Run the full feature engineering pipeline.
    
    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame from clean.py
    bank_col : str
        Column name for the bank/lender identifier.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with all engineered features added.
    """
    print("Building feature matrix...")
    
    print("  → Loan structure features")
    df = add_loan_structure_features(df)
    
    print("  → Borrower profile features")
    df = add_borrower_profile_features(df)
    
    print("  → Industry risk features")
    df = add_industry_risk_features(df)
    
    print("  → Economic cycle features")
    df = add_economic_cycle_features(df)
    
    print("  → Bank quality features (leak-safe)")
    df = add_bank_quality_features(df, bank_col=bank_col)
    
    print("  → Derived risk signals")
    df = add_derived_risk_signals(df)
    
    print(f"  ✓ Feature matrix complete: {len(df.columns)} total columns")
    return df
