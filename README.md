# SBA Loan Charge-Off Prediction & Expected Loss Engine

## Business Problem
Community banks that originate SBA-backed loans need to assess charge-off risk at approval time. Even with the SBA guarantee covering 75-85%, the bank still loses the unguaranteed portion — averaging ~$47K per charge-off. This model predicts default probability and calculates expected dollar loss per loan using the Basel II/III Expected Loss framework.

## Expected Loss Framework

$$EL = PD \times LGD \times EAD$$

- **PD (Probability of Default)** — XGBoost classifier's predicted probability
- **LGD (Loss Given Default)** — `(GrAppv - SBA_Appv) / GrAppv` (unguaranteed portion)
- **EAD (Exposure at Default)** — `GrAppv` (total loan amount)

## Dataset
[SBA 7(a) & 504 FOIA Data](https://data.sba.gov/en/dataset/7-a-504-foia) — Real U.S. government loan data from the SBA's Freedom of Information Act (FOIA) releases, covering FY1991–Present.

## Key Results
- **Model:** XGBoost — PR-AUC = TBD, ROC-AUC = TBD
- **Business Impact:** TBD
- **Key Insight:** Moral hazard analysis of SBA guarantee ratios

## Project Structure
```
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_modeling.ipynb
│   └── 05_shap_and_expected_loss.ipynb
├── src/
│   ├── clean.py              # Data cleaning functions
│   ├── features.py            # Feature engineering (leak-safe)
│   ├── pipeline.py            # sklearn Pipeline definition
│   ├── evaluate.py            # Custom metrics (PR-AUC, precision@k, EL accuracy)
│   ├── expected_loss.py       # PD × LGD × EAD calculation
│   └── risk_tiers.py          # PD → risk tier mapping
├── app/
│   └── streamlit_app.py       # Full risk assessment UI
├── models/                    # Saved model artifacts (.pkl)
├── reports/figures/           # Saved EDA + SHAP plots
├── data/                      # Raw & processed data (git-ignored)
├── requirements.txt
└── .gitignore
```

## Technical Highlights
- Temporal train/test split (no random split data leakage)
- Leak-safe bank-level and industry-level feature engineering
- SHAP-based explainable risk tiers for loan officer decision support
- Moral hazard analysis of SBA guarantee ratios
- Streamlit app with what-if scenarios and portfolio batch upload

## Setup
```bash
# Clone the repo
git clone <repo-url>
cd sba-loan-risk-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download data
# Place the 7(a) FOIA CSV files into data/raw/
# Download from: https://data.sba.gov/en/dataset/7-a-504-foia

# Run notebooks in order (01 → 05)

# Launch Streamlit app
streamlit run app/streamlit_app.py
```

## License
MIT
