"""
clean.py — Data cleaning functions for the SBA 7(a) FOIA dataset.

Handles:
- Loading and merging multiple FOIA CSV files
- Currency column parsing ($, commas)
- Date parsing (ApprovalDate, DisbursementDate, ChgOffDate)
- Target variable construction from MIS_Status
- Standardizing categorical fields (RevLineCr, LowDoc, NewExist)
- NAICS code validation and cleaning
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_and_merge_foia_files(data_dir: str) -> pd.DataFrame:
    """
    Load all 7(a) FOIA CSV files from data/raw/ and concatenate into a single DataFrame.
    
    Parameters
    ----------
    data_dir : str
        Path to the directory containing raw FOIA CSV files.
    
    Returns
    -------
    pd.DataFrame
        Merged DataFrame of all 7(a) loan records.
    """
    data_path = Path(data_dir)
    csv_files = sorted(data_path.glob("FOIA*7*a*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(
            f"No 7(a) FOIA CSV files found in {data_dir}. "
            "Download from: https://data.sba.gov/en/dataset/7-a-504-foia"
        )
    
    dfs = []
    for f in csv_files:
        print(f"  Loading {f.name} ...")
        df = pd.read_csv(f, dtype=str, low_memory=False)
        dfs.append(df)
        print(f"    → {len(df):,} rows, {len(df.columns)} columns")
    
    merged = pd.concat(dfs, ignore_index=True)
    print(f"\n  Total merged: {len(merged):,} rows")
    return merged


def parse_currency(series: pd.Series) -> pd.Series:
    """
    Convert currency strings like '$1,234,567.89' to float.
    Handles missing values gracefully.
    """
    return (
        series
        .astype(str)
        .str.replace(r'[$,]', '', regex=True)
        .str.strip()
        .replace(['', 'nan', 'None'], np.nan)
        .astype(float)
    )


def parse_date(series: pd.Series, dayfirst: bool = False) -> pd.Series:
    """
    Parse date strings to datetime, coercing errors to NaT.
    """
    return pd.to_datetime(series, errors='coerce', dayfirst=dayfirst)


def clean_target(df: pd.DataFrame, col: str = 'MIS_Status') -> pd.DataFrame:
    """
    Create binary target variable from MIS_Status.
    
    - 'CHGOFF' → 1 (Charged Off / Default)
    - 'P I F'  → 0 (Paid in Full)
    - Other    → dropped
    
    Returns
    -------
    pd.DataFrame
        DataFrame with rows filtered to valid targets and a new 'target' column.
    """
    df = df.copy()
    df[col] = df[col].astype(str).str.strip().str.upper()
    
    valid_mask = df[col].isin(['CHGOFF', 'P I F', 'PIF'])
    print(f"  Dropping {(~valid_mask).sum():,} rows with invalid MIS_Status")
    df = df[valid_mask].copy()
    
    df['target'] = (df[col] == 'CHGOFF').astype(int)
    return df


def clean_binary_flag(series: pd.Series) -> pd.Series:
    """
    Standardize messy binary columns (RevLineCr, LowDoc) to clean 0/1.
    Maps Y/1/T → 1, N/0/F → 0, else NaN.
    """
    mapping = {
        'Y': 1, 'y': 1, '1': 1, 'T': 1, 't': 1, 'YES': 1,
        'N': 0, 'n': 0, '0': 0, 'F': 0, 'f': 0, 'NO': 0,
    }
    return series.astype(str).str.strip().map(mapping)


def clean_naics(series: pd.Series) -> pd.Series:
    """
    Clean NAICS codes — ensure 6-digit string, extract 2-digit sector.
    Returns the 2-digit NAICS sector code.
    """
    cleaned = series.astype(str).str.strip().str[:6]
    # Extract first 2 digits as sector
    sector = cleaned.str[:2]
    # Mark invalid sectors
    sector = sector.where(sector.str.isnumeric(), other=np.nan)
    return sector


def run_full_cleaning_pipeline(raw_dir: str, save_path: str = None) -> pd.DataFrame:
    """
    Execute the complete cleaning pipeline end-to-end.
    
    Parameters
    ----------
    raw_dir : str
        Path to directory containing raw FOIA CSV files.
    save_path : str, optional
        If provided, saves the cleaned DataFrame as a parquet file.
    
    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame ready for feature engineering.
    """
    print("=" * 60)
    print("STEP 1: Loading & merging FOIA files")
    print("=" * 60)
    df = load_and_merge_foia_files(raw_dir)
    
    print("\nSTEP 2: Parsing currency columns")
    currency_cols = ['GrAppv', 'SBA_Appv', 'ChgOffPrinGr', 'DisbursementGross']
    for col in currency_cols:
        if col in df.columns:
            df[col] = parse_currency(df[col])
            print(f"  {col}: {df[col].notna().sum():,} valid values")
    
    print("\nSTEP 3: Parsing date columns")
    date_cols = ['ApprovalDate', 'DisbursementDate', 'ChgOffDate']
    for col in date_cols:
        if col in df.columns:
            df[col] = parse_date(df[col])
            print(f"  {col}: {df[col].notna().sum():,} valid dates")
    
    print("\nSTEP 4: Cleaning target variable (MIS_Status)")
    df = clean_target(df)
    print(f"  Target distribution:\n{df['target'].value_counts()}")
    
    print("\nSTEP 5: Cleaning binary flags")
    if 'RevLineCr' in df.columns:
        df['is_revolving'] = clean_binary_flag(df['RevLineCr'])
    if 'LowDoc' in df.columns:
        df['is_low_doc'] = clean_binary_flag(df['LowDoc'])
    
    print("\nSTEP 6: Cleaning NAICS codes")
    if 'NAICS' in df.columns:
        df['naics_sector'] = clean_naics(df['NAICS'])
        print(f"  Valid NAICS sectors: {df['naics_sector'].notna().sum():,}")
    
    print("\nSTEP 7: Parsing numeric columns")
    numeric_cols = ['Term', 'NoEmp', 'CreateJob', 'RetainedJob', 'ApprovalFY']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print("\nSTEP 8: Cleaning NewExist")
    if 'NewExist' in df.columns:
        df['NewExist'] = pd.to_numeric(df['NewExist'], errors='coerce')
        df['is_new_business'] = (df['NewExist'] == 2).astype(int)
    
    if save_path:
        df.to_parquet(save_path, index=False)
        print(f"\n  Saved cleaned data to {save_path}")
    
    print(f"\n{'=' * 60}")
    print(f"CLEANING COMPLETE: {len(df):,} rows, {len(df.columns)} columns")
    print(f"  Default rate: {df['target'].mean():.2%}")
    print(f"{'=' * 60}")
    
    return df
