# 🏦 SBA Loan Credit Risk Assessment Engine: Full Project Report

This document serves as a comprehensive, highly detailed portfolio report of the end-to-end machine learning lifecycle for the SBA Loan Risk Assessment project. It breaks down every major phase, decision, and technical implementation.

---

## Phase 1: Data Cleaning & Target Definition

The project began with a raw dataset of over 1.9 million historical SBA 7(a) loan records obtained via FOIA.

### Target Variable Definition
The raw `loanstatus` column contained 9 distinct statuses. To frame this as a binary classification problem for credit risk, we defined:
* **Default (Target = 1):** `CHGOFF` (Charged Off), `LIQUID` (Liquidation of collateral), and `SOLDSECMKT` (Sold on Secondary Market due to distress).
* **Safe (Target = 0):** `PIF` (Paid in Full) and `CANCLD` (Cancelled before disbursement).

### Handling Systematic Missingness
During EDA, we discovered a classic case of **Systematic Missingness** (Missing Not at Random - MNAR). The highly predictive `initialinterestrate` feature had a 61% missing rate globally.
* **Finding:** 100% of interest rates were missing in the 1990s and 95% in the 2000s, but 0% were missing from 2010 onwards.
* **Decision:** Rather than dropping this critical feature or performing massive imputation that would distort the model, we temporally filtered the dataset to only include loans from **2010 to Present**. This preserved 515,000+ records of clean, fully populated data highly relevant to the modern post-2008 financial environment.

---

## Phase 2: Exploratory Data Analysis (EDA) & Insights

Our EDA surfaced several critical economic and behavioral insights that guided feature engineering:

1. **The Moral Hazard Problem:** 
   Loans backed by an 85% government guarantee exhibited an actual default rate of **13.1%**, while those backed by a 75% guarantee defaulted at only **7.8%**. This stark contrast provides empirical evidence of moral hazard—when banks have less of their own capital at risk, underwriting standards demonstrably loosen.
2. **Macroeconomic Sensitivity:** 
   The SBA portfolio proved highly sensitive to Federal Reserve monetary policy. Following the aggressive rate hikes starting in 2022, the overall default rate spiked from a historical average of ~8% up to **24% in 2023**, devastating variable-rate borrowers.
3. **Industry Risk Profiling:** 
   Retail (NAICS 44/45) and Transportation (NAICS 48) proved to be the riskiest sectors (~11.5% default rate), whereas Management of Companies (NAICS 55) was the safest (3.4%).

---

## Phase 3: Advanced Feature Engineering

To capture institutional risk without causing data leakage, we implemented sophisticated feature engineering techniques.

### Leak-Safe Historical Default Rates
We needed to capture that some banks (and some industry sectors) are historically riskier than others. However, using the global average default rate of a bank would cause **target leakage**, as it includes future knowledge of whether the current loan defaults.
* **Solution:** We calculated **cumulative, expanding-window default rates** grouped by Bank and Sector, shifted by one row. For any given loan, the model only sees the bank's default rate *up to the day before that loan was approved*. 
* This resulted in highly predictive, leak-safe features: `bank_prior_def_rate` and `sector_historical_default_rate`.

### LGD & EAD Features
We engineered financial exposure features essential for the downstream Loss Engine:
* `unguaranteed_exposure`: The absolute dollar amount the bank stands to lose (Gross Approval - SBA Guarantee).

---

## Phase 4: Modeling Strategy

### Temporal Split
To simulate a real-world production environment, we avoided random train/test splits. Instead, we used an Out-Of-Time (OOT) validation strategy:
* **Train Set:** Loans approved between 2010 and 2020.
* **Test Set:** Loans approved between 2021 and 2026.
* This stress-tested the model's ability to generalize to the massive macroeconomic shift (inflation/rate hikes) that occurred in 2022-2023.

### Model Selection & Tuning
1. **Baseline:** We established a Logistic Regression baseline (ROC-AUC ~0.71).
2. **Champion Model:** We selected Scikit-Learn's **`HistGradientBoostingClassifier`** because it natively handles missing values and categoricals, and is exponentially faster than standard Random Forests on half a million rows.
3. **Class Imbalance:** We utilized `class_weight='balanced'` in the scikit-learn pipeline to penalize the model more heavily for missing defaults (the minority class, ~8.7%).
4. **Final Performance:** The tuned pipeline achieved an impressive **0.7506 ROC-AUC**, proving highly capable of ranking risky loans.

---

## Phase 5: Explainable AI (XAI) with SHAP

Credit risk models cannot be "black boxes" due to regulatory requirements (e.g., Equal Credit Opportunity Act). We integrated **SHAP (SHapley Additive exPlanations)** via `TreeExplainer`.

* **Global Explainability (Beeswarm):** We proved that loan duration (`terminmonths`), interest rates (`initialinterestrate`), and our engineered `bank_prior_def_rate` were the top drivers of default globally.
* **Local Explainability (Waterfall):** For any single loan application, the model generates a waterfall chart quantifying exactly how many percentage points each feature added to, or subtracted from, the final default probability.

---

## Phase 6: The Expected Loss (EL) Engine

Machine learning outputs a raw probability, but bank risk managers think in dollars. We implemented the **Basel II/III Expected Loss framework**:

> **Expected Loss (EL) = PD × LGD × EAD**

* **PD (Probability of Default):** The raw probability output from the `predict_proba()` method.
* **LGD (Loss Given Default):** Calculated dynamically as the unguaranteed portion of the loan divided by the total loan amount. (e.g., A 75% guarantee = 25% LGD).
* **EAD (Exposure at Default):** The total loan amount requested.

### Risk Tiering
We mapped the continuous PD scores into 4 actionable, monotonically ordered Risk Tiers:
* 🟢 **Tier 1 - Auto Approve:** (Actual default rate: 3.7%)
* 🟡 **Tier 2 - Manual Review:** (Actual default rate: 8.3%)
* 🟠 **Tier 3 - Senior Review:** (Actual default rate: 13.7%)
* 🔴 **Tier 4 - Recommend Denial:** (Actual default rate: 30.4%)
* *Insight: A loan officer following these automated tiers would avoid 8x more charge-offs than random selection.*

---

## Phase 7: Streamlit Deployment & UI Breakdown

The entire pipeline was deployed into a production-grade, dark-themed Streamlit web application. 

### 1. The Landing Page
When no loan is currently being assessed, the app serves as a model dashboard. It displays:
* Key model performance metrics (ROC-AUC, PR-AUC).
* A 4-step "How It Works" workflow guide.
* The 3 critical macroeconomic research findings discovered during EDA (Moral Hazard, Fed Rate Impact, Industry Risk).

### 2. The Sidebar (Input Panel)
The sidebar acts as the loan officer's data entry terminal, structured logically into:
* **Loan Structure:** Inputs for Loan Amount, Guarantee %, Term, Interest Rate, and Rate Type. (The SBA Guarantee dollar amount updates dynamically as the slider moves).
* **Borrower Profile:** Dropdowns for Industry Sector (mapped to 24 NAICS codes), Business Age, Business Type, and Franchise status.
* **Lender Information:** Details regarding the bank's historical SBA experience and default rate, allowing the model to utilize our leak-safe institutional risk features.

### 3. The Output Tabs (Post-Assessment)
Clicking "Assess Risk" runs the inputs through the serialized `HistGradientBoosting` pipeline and generates three interactive tabs:

#### 📊 Tab 1: Risk Assessment
This is the primary financial dashboard for the loan.
* **Risk Tier Banner:** A color-coded banner dynamically displays the assigned Risk Tier (e.g., "🔴 TIER 4 — RECOMMEND DENIAL") alongside automated underwriting advice.
* **Top-Line Metrics:** Displays the raw PD %, the Expected Dollar Loss, the Bank's true financial exposure, and the SBA Guarantee coverage.
* **Formula Breakdown:** Visually lays out the Basel II/III math (PD × LGD × EAD = Expected Loss) so underwriters can see exactly how the dollar risk was calculated.
* **Loan Summary:** A clean table summarizing all the inputted features.

#### 🔍 Tab 2: SHAP Explanation
This tab ensures regulatory compliance and underwriter trust by explaining the model's logic.
* **Waterfall Plot:** A visual chart showing the baseline probability and how specific features of the application pushed the risk up (red bars) or down (blue bars).
* **Risk Drivers Summary:** Parses the SHAP values to present bulleted lists of the top 4 factors increasing risk and the top 4 factors mitigating risk.

#### 🔄 Tab 3: What-If Analysis
A dynamic scenario modeling tool.
* **The Concept:** Often, a loan is too risky at a 50% guarantee, but acceptable at an 85% guarantee.
* **Interactive Charting:** Generates a data table and a Matplotlib area chart plotting the Expected Dollar Loss against all possible SBA Guarantee percentages (50% to 90%).
* **Insight Generation:** An automated info box calculates exactly how much risk the bank sheds by requesting the maximum SBA guarantee.
