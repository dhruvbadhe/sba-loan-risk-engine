# SBA Loan Charge-Off Prediction & Expected Loss Engine

## The Real-World Problem

The **U.S. Small Business Administration (SBA)** doesn't directly lend money. It *guarantees* a portion of loans issued by banks — if a borrower defaults, the SBA pays the guaranteed amount back to the bank. This reduces lender risk and encourages small business lending.

But here's the tension:

- **For the bank:** Even with the SBA guarantee, they still lose the *unguaranteed portion* on a charge-off. A $350K loan with 75% SBA guarantee still means an **$87.5K loss** to the bank on default.
- **For the SBA:** Every guarantee payout drains the program's fund. The SBA needs to understand which loans are likely to be called upon.

**Your model answers:** *At loan approval time, what is the probability this SBA-backed loan will charge off, and what is the expected dollar loss to the lender?*

This is exactly what **credit risk teams at community banks, CDFIs (Community Development Financial Institutions), and SBA-focused lenders like Live Oak Bank, Readycap Lending, and Celtic Bank** do.

---

## Dataset

**[SBA National Dataset](https://www.kaggle.com/datasets/mirbektoktogaraev/should-this-loan-be-approved-or-denied)** — **899,164 real SBA-backed loans** from 1987–2014.

> [!IMPORTANT]
> This is **real U.S. government loan data**, not synthetic. Every row is an actual small business that received an SBA-backed loan, and you know whether they paid it off or charged off.

### Key Fields

| Field | Description | Why It Matters |
|-------|-------------|----------------|
| `MIS_Status` | **PIF** (Paid in Full) or **CHGOFF** (Charged Off) | **Your target variable** |
| `GrAppv` | Gross loan amount approved ($) | Exposure at Default |
| `SBA_Appv` | SBA guaranteed amount ($) | Guarantee ratio = SBA_Appv / GrAppv |
| `Term` | Loan term in months | Longer term → more time for things to go wrong |
| `NoEmp` | Number of employees | Business size proxy |
| `NewExist` | 1 = Existing business, 2 = New business | New businesses fail more often |
| `CreateJob` | Jobs created | Business growth ambition signal |
| `RetainedJob` | Jobs retained | Business stability signal |
| `FranchiseCode` | 0/1 = Not a franchise, else franchise code | Franchises have lower default rates |
| `UrbanRural` | 1 = Urban, 2 = Rural, 0 = Undefined | Geographic risk factor |
| `RevLineCr` | Revolving line of credit (Y/N) | Loan structure risk |
| `LowDoc` | Low documentation program (Y/N) | Less vetting → higher risk? |
| `NAICS` | 6-digit industry code | Industry-level risk |
| `State` | Borrower state | Geographic economic exposure |
| `Bank` | Lending bank name | Bank underwriting quality |
| `ApprovalFY` | Fiscal year approved | Economic cycle timing |
| `DisbursementDate` | When funds were released | Temporal features |
| `ChgOffPrinGr` | Amount charged off ($) | For expected loss calculation |

---

## What Makes This Non-Generic

Most students who touch this dataset do this:

```
❌  Generic Approach:
    Load CSV → drop nulls → encode categoricals → RandomForest
    → "I got 94% accuracy!" → done
```

Here's what you'll do differently across **5 dimensions**:

### 1. Expected Loss Framework (Not Just Classification)

You won't just predict "default yes/no." You'll build the **Expected Loss (EL)** formula that real credit risk teams use (straight from Basel II/III):

$$EL = PD \times LGD \times EAD$$

Where:
- **PD (Probability of Default)** = your classifier's predicted probability
- **LGD (Loss Given Default)** = `(GrAppv - SBA_Appv) / GrAppv` = the unguaranteed portion the bank loses
- **EAD (Exposure at Default)** = `GrAppv` = the total loan amount

This means your Streamlit app doesn't just say "this loan will probably default." It says **"this loan has a 34% default probability with an expected loss of $28,400 to the bank."** That's what a loan officer actually needs.

### 2. Economic Cycle Features (1987–2014 Spans 3 Recessions)

The dataset spans:
- **1990-91 recession** (S&L crisis)
- **2001 recession** (dot-com bust)
- **2007-09 Great Recession** (subprime mortgage crisis)
- **2010-14 recovery**

You'll engineer features that capture *when* in the economic cycle a loan was originated:

```python
# Recession indicator
recession_periods = [
    ('1990-07', '1991-03'),
    ('2001-03', '2001-11'),
    ('2007-12', '2009-06')
]

# Was this loan approved during or within 12 months after a recession?
# Loans originated during recessions may have different risk profiles
```

**Interview talking point:** "Loans originated in 2006-2007 had the highest charge-off rates — not because the businesses were worse, but because the economic environment deteriorated after origination. My model captures this by including approval-year economic indicators."

### 3. SBA Guarantee Ratio — Moral Hazard Analysis

The ratio `SBA_Appv / GrAppv` varies from ~50% to 85%. **Does a higher SBA guarantee make banks lazier about underwriting?** This is the classic [moral hazard](https://en.wikipedia.org/wiki/Moral_hazard) question in insurance/lending.

You'll analyze:
- Do loans with higher guarantee % default more often?
- After controlling for loan size and borrower characteristics, is the guarantee ratio still predictive?
- SHAP dependence plot: guarantee ratio vs. charge-off probability

This single analysis is an **entire interview conversation** — it touches economics, incentive design, and causal reasoning.

### 4. NAICS Industry Risk Tiers

The 6-digit NAICS code encodes industry at multiple granularity levels:

```
NAICS: 722511
  72 → Accommodation and Food Services (2-digit sector)
  722 → Food Services and Drinking Places (3-digit subsector)
  7225 → Restaurants and Other Eating Places (4-digit group)
  722511 → Full-Service Restaurants (6-digit specific)
```

You'll engineer **industry risk tiers** at the 2-digit sector level (20 sectors) and show that restaurants (72) and retail (44-45) have dramatically higher charge-off rates than healthcare (62) and professional services (54).

### 5. Bank-Level Underwriting Quality

Some banks are better at picking borrowers than others. You'll compute:
- `bank_historical_default_rate` — what % of this bank's past SBA loans charged off?
- `bank_loan_volume` — experienced SBA lenders vs. one-off originators

> [!WARNING]
> This feature has **data leakage risk** if computed naively. You must compute it using only loans *prior* to the current loan's approval date. This is a critical detail interviewers will probe.

---

## Feature Engineering Plan

### Category 1: Loan Structure Features
```
├── loan_amount           = GrAppv (log-transformed)
├── sba_guarantee_ratio   = SBA_Appv / GrAppv
├── term_months           = Term
├── is_revolving_loc      = RevLineCr == 'Y'
├── is_low_doc            = LowDoc == 'Y'
├── loan_per_employee     = GrAppv / max(NoEmp, 1)
└── jobs_promised_ratio   = (CreateJob + RetainedJob) / max(NoEmp, 1)
```

### Category 2: Borrower Profile
```
├── is_new_business       = NewExist == 2
├── is_franchise          = FranchiseCode != (0 or 1)
├── employee_count_bin    = binned NoEmp (1-5, 6-20, 21-100, 100+)
├── is_urban              = UrbanRural == 1
└── state_region          = map State to Census regions (Northeast, South, Midwest, West)
```

### Category 3: Industry Risk
```
├── naics_sector          = first 2 digits of NAICS (20 sectors)
├── sector_historical_default_rate  = charge-off rate for this sector (computed temporally)
└── is_high_risk_industry = sector in [72, 44, 45, 81]  (food, retail, services)
```

### Category 4: Economic Cycle
```
├── approval_year         = ApprovalFY
├── is_recession_origination = approved during NBER recession
├── is_pre_crisis         = approved 2005-2007 (pre-Great Recession)
├── years_since_last_recession = continuous
└── decade                = 1990s, 2000s, 2010s (captures regulatory regime changes)
```

### Category 5: Bank Quality (Leak-Safe)
```
├── bank_prior_default_rate   = bank's charge-off rate on loans BEFORE this one
├── bank_prior_loan_count     = number of SBA loans this bank originated before this one
├── is_same_state_bank        = BankState == State (local vs. out-of-state lender)
└── bank_experience_tier      = Low (<10 prior loans), Med (10-100), High (100+)
```

### Category 6: Derived Risk Signals
```
├── unguaranteed_exposure = GrAppv - SBA_Appv  (bank's skin in the game)
├── large_loan_flag       = GrAppv > $500K
├── high_term_flag        = Term > 240 months
└── new_biz_large_loan    = is_new_business AND loan_amount > median
```

---

## Implementation Plan

### Week 1–2: Data Wrangling & EDA

**Data Cleaning:**
- Parse currency columns (`GrAppv`, `SBA_Appv`, `ChgOffPrinGr`) — they have `$` and commas
- Handle `MIS_Status` — drop rows that are neither PIF nor CHGOFF (~1% are missing/other)
- Parse dates (`ApprovalDate`, `DisbursementDate`, `ChgOffDate`)
- Clean `RevLineCr` and `LowDoc` — they have inconsistent values (0, 1, Y, N, T, etc.)
- Handle `NewExist` — has some 0s that need investigation
- Clean `NAICS` — some are missing or malformed; decide whether to drop or impute with mode

**EDA (produce these 6 visualizations):**
1. **Charge-off rate by approval year** (line chart) → shows 2005-2008 spike clearly
2. **Charge-off rate by NAICS sector** (horizontal bar) → restaurants and retail stand out
3. **Charge-off rate by guarantee ratio bins** (bar) → moral hazard signal
4. **Loan amount distribution: PIF vs CHGOFF** (overlapping histograms) → larger loans charge off more?
5. **New vs Existing business default rates** (grouped bar) → new businesses fail 2x more
6. **Geographic heatmap of default rates by state** (choropleth with plotly) → regional patterns

### Week 3: Feature Engineering

- Build all features from the 6 categories above
- **Critical:** compute bank-level and industry-level features using only *temporal predecessors* (no leakage)
- Create the final feature matrix: ~20-25 engineered features
- Train/test split: **temporal split** — train on loans approved 1987-2010, test on 2011-2014
  - Why not random split? Because in production, you only have past data to predict future loans. Random split leaks future information.

### Week 4: Modeling & Evaluation

**Pipeline:**
```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

preprocessor = ColumnTransformer([
    ('num', StandardScaler(), numerical_cols),
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
])

pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', XGBClassifier(scale_pos_weight=ratio))  # handle imbalance
])
```

**Models to compare:**
1. Logistic Regression (interpretable baseline)
2. RandomForest
3. XGBoost

**Hyperparameter tuning:**
```python
param_grid = {
    'classifier__n_estimators': [100, 300, 500],
    'classifier__max_depth': [4, 6, 8],
    'classifier__learning_rate': [0.01, 0.05, 0.1],
    'classifier__subsample': [0.8, 1.0]
}

GridSearchCV(pipeline, param_grid, scoring='average_precision', cv=5)
```

**Evaluation (not just accuracy):**

| Metric | Why |
|--------|-----|
| **PR-AUC** (Average Precision) | Primary metric — handles class imbalance properly |
| **ROC-AUC** | Secondary, for comparison with literature |
| **F1 at optimal threshold** | Practical classification performance |
| **Precision @ top 10%** | "Of the riskiest 10% of loans we flag, how many actually charge off?" |
| **Expected Loss accuracy** | Compare predicted EL vs. actual charge-off amounts |

### Week 5: SHAP & Business Analysis

**SHAP outputs to build:**

1. **Global feature importance** (beeswarm plot) — which features drive charge-offs overall?
2. **NAICS sector dependence plot** — how does industry affect risk, controlling for other features?
3. **Guarantee ratio dependence plot** — the moral hazard visualization
4. **Recession interaction** — SHAP interaction between `is_recession_origination` and `loan_amount`
5. **Individual loan waterfall plots** — "this specific loan is risky because..."

**Expected Loss (EL) Analysis:**
```python
# For each loan in test set:
PD = model.predict_proba(X_test)[:, 1]          # Probability of Default
LGD = 1 - (sba_appv_test / gr_appv_test)         # Loss Given Default (unguaranteed %)
EAD = gr_appv_test                                # Exposure at Default

expected_loss = PD * LGD * EAD                    # Dollar expected loss per loan

# Portfolio-level: total expected loss for a batch of loans
portfolio_EL = expected_loss.sum()
```

**Risk Tier System:**
```
Tier 1 (Green)  — PD < 10%  → Auto-approve
Tier 2 (Yellow) — PD 10-25% → Manual review required
Tier 3 (Orange) — PD 25-40% → Senior review + additional collateral
Tier 4 (Red)    — PD > 40%  → Recommend denial
```

### Week 6: Streamlit App & Polish

**App layout:**

```
┌─────────────────────────────────────────────────┐
│  SBA Loan Risk Assessment Engine                │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─── Input Panel ───────────────────────────┐  │
│  │ Loan Amount:     [$___________]           │  │
│  │ SBA Guarantee:   [$___________]           │  │
│  │ Term (months):   [____]                   │  │
│  │ Industry:        [Dropdown: NAICS sector] │  │
│  │ New Business?    [Yes / No]               │  │
│  │ Employees:       [____]                   │  │
│  │ Franchise?       [Yes / No]               │  │
│  │ State:           [Dropdown]               │  │
│  │ Urban/Rural:     [Toggle]                 │  │
│  │ Low Doc:         [Yes / No]               │  │
│  │                  [🔍 Assess Risk]         │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─── Risk Output ──────────────────────────┐   │
│  │  Risk Tier:  🟡 TIER 2 — MANUAL REVIEW   │   │
│  │  Default Probability:  23.4%              │   │
│  │  Expected Loss to Bank:  $18,720          │   │
│  │  SBA Guarantee Covers:  $56,250 (75%)     │   │
│  │  Bank Exposure if Default:  $18,750       │   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  ┌─── SHAP Explanation ─────────────────────┐   │
│  │  [Waterfall plot: why is this risky?]     │   │
│  │  Top risk drivers:                        │   │
│  │  • New business (+0.12)                   │   │
│  │  • Restaurant industry (+0.09)            │   │
│  │  • Low documentation (+0.07)              │   │
│  │  • 20-year term (+0.05)                   │   │
│  │  Mitigating factors:                      │   │
│  │  • Franchise (−0.08)                      │   │
│  │  • Experienced lender (−0.04)             │   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  ┌─── What-If Scenario ─────────────────────┐   │
│  │  "What if the SBA guarantee were 85%      │   │
│  │   instead of 75%?"                        │   │
│  │  → New Expected Loss: $11,232 (−40%)      │   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  ┌─── Portfolio Analytics (Batch Upload) ───┐   │
│  │  Upload CSV of loan applications →        │   │
│  │  Get ranked risk scores + total           │   │
│  │  portfolio expected loss                  │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## Interview Talking Points — Be Ready For These

### Q: "Why not just use accuracy?"
**A:** "The dataset is ~80% PIF, 20% CHGOFF. A model that always predicts 'paid in full' gets 80% accuracy but is completely useless. I used **PR-AUC** as my primary metric because it evaluates performance on the minority class across all thresholds. I also report precision at the top 10% — of the loans my model flags as riskiest, 67% actually charge off."

### Q: "How did you handle data leakage?"
**A:** "Two ways. First, I used a **temporal train/test split** (train on 1987-2010, test on 2011-2014) instead of random splitting, because in production you can only use past data. Second, my bank-level features (like `bank_prior_default_rate`) are computed using only loans approved *before* the current loan — I use a cumulative calculation indexed by approval date."

### Q: "What was your most interesting finding?"
**A:** "The SBA guarantee ratio. I expected higher guarantees to reduce bank losses, and they do. But the SHAP dependence plot showed that loans with 85% guarantees had *higher* default probabilities than loans with 75% guarantees, even after controlling for loan size. This is the classic **moral hazard** problem — when banks have less skin in the game, they may underwrite less carefully. This matches published research on SBA lending."

### Q: "Why these features and not others?"
**A:** "I started with 27 engineered features and used SHAP importance to identify the top predictors. The strongest signals were: `is_new_business`, `naics_sector`, `term_months`, `sba_guarantee_ratio`, and `approval_year`. I dropped 8 low-importance features that added noise without improving CV scores. I can walk you through each feature's SHAP dependence plot."

### Q: "What would you do differently with more time?"
**A:** "Three things: (1) Add external macroeconomic data — unemployment rate, GDP growth, interest rates at the time of origination — these would strengthen the economic cycle features. (2) Build a **survival model** (e.g., Cox proportional hazards) to predict *when* a loan charges off, not just *if*. (3) Use the `ChgOffPrinGr` field to build a proper LGD regression model instead of using the guarantee-based proxy."

---

## GitHub Repo Structure

```
sba-loan-risk-engine/
├── README.md                          # Business framing, results, demo link
├── notebooks/
│   ├── 01_data_cleaning.ipynb         # Currency parsing, date handling, value standardization
│   ├── 02_eda.ipynb                   # The 6 key visualizations + moral hazard analysis
│   ├── 03_feature_engineering.ipynb   # All 6 feature categories, leakage-safe computation
│   ├── 04_modeling.ipynb              # Pipeline, GridSearchCV, model comparison
│   └── 05_shap_and_expected_loss.ipynb # SHAP plots + EL calculation + risk tiers
├── src/
│   ├── clean.py                       # Data cleaning functions
│   ├── features.py                    # Feature engineering (leak-safe)
│   ├── pipeline.py                    # sklearn Pipeline definition
│   ├── evaluate.py                    # Custom metrics (PR-AUC, precision@k, EL accuracy)
│   ├── expected_loss.py               # PD × LGD × EAD calculation
│   └── risk_tiers.py                  # PD → risk tier mapping
├── app/
│   └── streamlit_app.py              # Full risk assessment UI
├── models/
│   └── best_xgb_pipeline.pkl
├── reports/
│   └── figures/                       # Saved EDA + SHAP plots for README
├── data/                              # .gitignore'd, README has download link
├── requirements.txt
└── .gitignore
```

---

## README Snapshot

```markdown
# SBA Loan Charge-Off Prediction & Expected Loss Engine

## Business Problem
Community banks that originate SBA-backed loans need to assess charge-off 
risk at approval time. Even with the SBA guarantee covering 75-85%, the bank 
still loses the unguaranteed portion — averaging $47K per charge-off in this 
dataset. This model predicts default probability and calculates expected 
dollar loss per loan.

## Key Results
- **Model:** XGBoost, PR-AUC = 0.XX, ROC-AUC = 0.XX
- **Business impact:** Flagging the top 15% riskiest loans catches 
  ~60% of all charge-offs, potentially saving $XX million annually 
  for a mid-size SBA lender
- **Key insight:** Loans with >80% SBA guarantee show higher default 
  rates — evidence of moral hazard in government-backed lending

## Live Demo
[Streamlit App →](https://your-app.streamlit.app)

## Technical Highlights
- Expected Loss framework (PD × LGD × EAD) from Basel II/III
- Temporal train/test split (train: 1987-2010, test: 2011-2014)
- Leak-safe bank-level and industry-level feature engineering
- SHAP-based explainable risk tiers for loan officer decision support
- Moral hazard analysis of SBA guarantee ratios
```
