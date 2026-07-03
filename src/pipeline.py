"""
pipeline.py — sklearn Pipeline definition for SBA loan charge-off prediction.

Defines the preprocessing + model pipeline with:
- StandardScaler for numerical features
- OneHotEncoder for categorical features
- XGBClassifier with class imbalance handling
"""

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier


# ---------------------------------------------------------------------------
# Default feature column lists — update after final feature selection
# ---------------------------------------------------------------------------
NUMERICAL_FEATURES = [
    'log_loan_amount',
    'sba_guarantee_ratio',
    'term_months',
    'loan_per_employee',
    'jobs_promised_ratio',
    'unguaranteed_exposure',
    'bank_prior_default_rate',
    'bank_prior_loan_count',
    'sector_historical_default_rate',
    'approval_year',
]

CATEGORICAL_FEATURES = [
    'naics_sector',
    'state_region',
    'employee_bin',
    'bank_experience_tier',
]

BINARY_FEATURES = [
    'is_new_business',
    'is_franchise',
    'is_urban',
    'is_revolving',
    'is_low_doc',
    'is_high_risk_industry',
    'is_recession_origination',
    'is_pre_crisis',
    'large_loan_flag',
    'high_term_flag',
    'new_biz_large_loan',
    'is_same_state_bank',
]


def build_preprocessor(
    numerical_cols: list = None,
    categorical_cols: list = None,
    binary_cols: list = None,
) -> ColumnTransformer:
    """
    Build the ColumnTransformer preprocessor.
    
    - Numerical: impute median → scale
    - Categorical: impute 'missing' → one-hot encode
    - Binary: impute 0 → pass through (already 0/1)
    """
    numerical_cols = numerical_cols or NUMERICAL_FEATURES
    categorical_cols = categorical_cols or CATEGORICAL_FEATURES
    binary_cols = binary_cols or BINARY_FEATURES
    
    num_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ])
    
    cat_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
    ])
    
    bin_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value=0)),
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_pipeline, numerical_cols),
            ('cat', cat_pipeline, categorical_cols),
            ('bin', bin_pipeline, binary_cols),
        ],
        remainder='drop',
    )
    
    return preprocessor


def build_pipeline(
    numerical_cols: list = None,
    categorical_cols: list = None,
    binary_cols: list = None,
    scale_pos_weight: float = 1.0,
    **xgb_kwargs,
) -> Pipeline:
    """
    Build the full sklearn Pipeline: preprocessor → XGBClassifier.
    
    Parameters
    ----------
    scale_pos_weight : float
        Ratio of negative to positive class count (handles imbalance).
    **xgb_kwargs
        Additional keyword arguments passed to XGBClassifier.
    
    Returns
    -------
    sklearn.pipeline.Pipeline
    """
    preprocessor = build_preprocessor(numerical_cols, categorical_cols, binary_cols)
    
    default_xgb_params = dict(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric='aucpr',
        random_state=42,
        n_jobs=-1,
    )
    default_xgb_params.update(xgb_kwargs)
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', XGBClassifier(**default_xgb_params)),
    ])
    
    return pipeline


def get_hyperparameter_grid() -> dict:
    """
    Return the hyperparameter search space for GridSearchCV / Optuna.
    """
    return {
        'classifier__n_estimators': [100, 300, 500],
        'classifier__max_depth': [4, 6, 8],
        'classifier__learning_rate': [0.01, 0.05, 0.1],
        'classifier__subsample': [0.8, 1.0],
        'classifier__colsample_bytree': [0.7, 0.8, 1.0],
    }
