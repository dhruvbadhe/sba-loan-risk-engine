"""
SBA Loan Risk Assessment Engine — Streamlit App
================================================
A production-grade credit risk assessment tool for SBA 7(a) loan officers.

Features:
- Individual loan risk assessment with PD, EL, and risk tier
- SHAP-based explainability (why is this loan risky?)
- What-if scenario analysis (guarantee ratio sensitivity)
- Portfolio batch upload and analysis
- Model performance dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
import os
import io

# ============================================================
# Page Config & Custom CSS
# ============================================================
st.set_page_config(
    page_title="SBA Loan Risk Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ---- Global ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ---- Header ---- */
    .main-header {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        margin: 0.5rem 0 0 0;
    }

    /* ---- Risk Tier Cards ---- */
    .tier-card {
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-weight: 700;
        font-size: 1.3rem;
        letter-spacing: 0.5px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    .tier-1 {
        background: linear-gradient(135deg, #064e3b, #059669);
        color: #ecfdf5;
        border: 1px solid #10b981;
    }
    .tier-2 {
        background: linear-gradient(135deg, #713f12, #ca8a04);
        color: #fefce8;
        border: 1px solid #eab308;
    }
    .tier-3 {
        background: linear-gradient(135deg, #7c2d12, #ea580c);
        color: #fff7ed;
        border: 1px solid #f97316;
    }
    .tier-4 {
        background: linear-gradient(135deg, #7f1d1d, #dc2626);
        color: #fef2f2;
        border: 1px solid #ef4444;
    }

    /* ---- Metric Cards ---- */
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .metric-card .label {
        color: #94a3b8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.3rem;
    }
    .metric-card .value {
        color: #f8fafc;
        font-size: 1.6rem;
        font-weight: 700;
    }
    .metric-card .sub {
        color: #64748b;
        font-size: 0.75rem;
        margin-top: 0.2rem;
    }

    /* ---- Info Box ---- */
    .info-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* ---- Sidebar Styling ---- */
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stSlider label {
        color: #e2e8f0;
        font-weight: 500;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* ---- Hide Streamlit Branding ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- Divider ---- */
    .custom-divider {
        border: 0;
        height: 1px;
        background: linear-gradient(to right, transparent, #334155, transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Load Model (cached so it only loads once)
# ============================================================
@st.cache_resource
def load_model():
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'best_hgb_pipeline.pkl')
    return joblib.load(model_path)

model = load_model()


# ============================================================
# Constants
# ============================================================
NAICS_SECTORS = {
    '11': '🌾 Agriculture, Forestry, Fishing',
    '21': '⛏️ Mining, Oil & Gas',
    '22': '⚡ Utilities',
    '23': '🏗️ Construction',
    '31': '🏭 Manufacturing (Food, Textiles)',
    '32': '🧪 Manufacturing (Wood, Chemical)',
    '33': '🔧 Manufacturing (Metals, Electronics)',
    '42': '📦 Wholesale Trade',
    '44': '🛒 Retail Trade (Stores)',
    '45': '🛍️ Retail Trade (Online, Other)',
    '48': '🚚 Transportation & Warehousing',
    '49': '📬 Postal & Courier Services',
    '51': '💻 Information & Media',
    '52': '🏛️ Finance & Insurance',
    '53': '🏠 Real Estate',
    '54': '📊 Professional & Technical Services',
    '55': '🏢 Management of Companies',
    '56': '🧹 Administrative & Waste Services',
    '61': '🎓 Educational Services',
    '62': '🏥 Health Care & Social Assistance',
    '71': '🎭 Arts, Entertainment & Recreation',
    '72': '🍽️ Accommodation & Food Services',
    '81': '🔨 Other Services (Repair, Personal)',
    '92': '🏛️ Public Administration',
}

ALL_FEATURES = [
    'grossapproval', 'sbaguaranteedapproval', 'terminmonths',
    'initialinterestrate', 'jobssupported', 'bank_prior_def_rate',
    'bank_prior_loans', 'sector_historical_default_rate',
    'unguaranteed_exposure', 'log_gross_approval',
    'naics_sector', 'businesstype', 'business_age_group', 'bank_experience_tier',
    'revolverstatus', 'is_same_state_bank', 'is_variable_rate',
    'is_franchise', 'collateralind',
]

SECTOR_DEFAULT_RATES = {
    '11': 0.053, '21': 0.073, '22': 0.058, '23': 0.095,
    '31': 0.088, '32': 0.088, '33': 0.088, '42': 0.087,
    '44': 0.115, '45': 0.115, '48': 0.115, '49': 0.102,
    '51': 0.089, '52': 0.058, '53': 0.073, '54': 0.078,
    '55': 0.034, '56': 0.090, '61': 0.091, '62': 0.058,
    '71': 0.111, '72': 0.094, '81': 0.088, '92': 0.089,
}


# ============================================================
# Helper Functions
# ============================================================
def get_risk_tier(pd_score):
    if pd_score < 0.10:
        return 1, '🟢 TIER 1 — AUTO APPROVE', 'tier-1', 'Low risk. Standard processing recommended.'
    elif pd_score < 0.25:
        return 2, '🟡 TIER 2 — MANUAL REVIEW', 'tier-2', 'Moderate risk. Manual underwriting review recommended.'
    elif pd_score < 0.40:
        return 3, '🟠 TIER 3 — SENIOR REVIEW', 'tier-3', 'Elevated risk. Senior credit officer review + additional collateral required.'
    else:
        return 4, '🔴 TIER 4 — RECOMMEND DENIAL', 'tier-4', 'High risk. Recommend denial or significant restructuring of loan terms.'


def render_metric(label, value, sub=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def build_input_df(loan_amount, sba_guarantee, term_months, interest_rate,
                   jobs_supported, naics_sector, business_type, business_age,
                   is_franchise, is_variable, is_revolving, has_collateral,
                   is_same_state, bank_prior_loans, bank_def_rate):
    return pd.DataFrame([{
        'grossapproval': float(loan_amount),
        'sbaguaranteedapproval': float(sba_guarantee),
        'terminmonths': float(term_months),
        'initialinterestrate': float(interest_rate),
        'jobssupported': float(jobs_supported),
        'bank_prior_def_rate': bank_def_rate / 100.0,
        'bank_prior_loans': float(bank_prior_loans),
        'sector_historical_default_rate': SECTOR_DEFAULT_RATES.get(naics_sector, 0.087),
        'unguaranteed_exposure': float(loan_amount - sba_guarantee),
        'log_gross_approval': np.log1p(float(loan_amount)),
        'naics_sector': naics_sector,
        'businesstype': business_type,
        'business_age_group': business_age,
        'bank_experience_tier': 'High' if bank_prior_loans >= 100 else ('Medium' if bank_prior_loans >= 10 else 'Low'),
        'revolverstatus': 1 if is_revolving else 0,
        'is_same_state_bank': 1 if is_same_state else 0,
        'is_variable_rate': 1 if is_variable else 0,
        'is_franchise': 1 if is_franchise else 0,
        'collateralind': 1 if has_collateral else 0,
    }])


# ============================================================
# Header
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>🏦 SBA Loan Risk Assessment Engine</h1>
    <p>Predict default probability • Calculate expected dollar loss • Explain risk drivers</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Sidebar — Loan Application Inputs
# ============================================================
with st.sidebar:
    st.markdown("## 📋 Loan Application")
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # --- Loan Structure ---
    st.markdown("### 💰 Loan Structure")
    loan_amount = st.number_input("Loan Amount ($)", min_value=5_000, max_value=5_000_000, value=250_000, step=10_000, format="%d")
    
    guarantee_pct = st.slider("SBA Guarantee (%)", min_value=50, max_value=90, value=75, step=5)
    sba_guarantee = int(loan_amount * guarantee_pct / 100)
    st.caption(f"SBA Guarantees: **${sba_guarantee:,}**")
    
    term_years = st.selectbox("Loan Term", ["5 years (60 mo)", "7 years (84 mo)", "10 years (120 mo)", "15 years (180 mo)", "20 years (240 mo)", "25 years (300 mo)"], index=2)
    term_months = int(term_years.split("(")[1].split(" ")[0])
    
    interest_rate = st.slider("Interest Rate (%)", min_value=2.0, max_value=14.0, value=7.5, step=0.25)
    is_variable = st.toggle("Variable Rate", value=True)
    is_revolving = st.toggle("Revolving Line of Credit", value=False)
    has_collateral = st.toggle("Collateral Provided", value=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # --- Borrower Profile ---
    st.markdown("### 👤 Borrower Profile")
    sector_label = st.selectbox("Industry Sector", list(NAICS_SECTORS.values()), index=17)
    naics_sector = [k for k, v in NAICS_SECTORS.items() if v == sector_label][0]

    business_age = st.selectbox("Business Age", ["Existing (5+ years)", "New (< 2 years)", "Unknown"], index=0)
    business_age_map = {"Existing (5+ years)": "Existing", "New (< 2 years)": "New", "Unknown": "Unknown"}
    business_age_val = business_age_map[business_age]

    business_type = st.selectbox("Business Type", ["CORPORATION", "INDIVIDUAL", "PARTNERSHIP"])
    is_franchise = st.toggle("Franchise", value=False)
    jobs_supported = st.number_input("Jobs Supported", min_value=0, max_value=500, value=10, step=1)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # --- Bank Info ---
    st.markdown("### 🏛️ Lender Information")
    is_same_state = st.toggle("Bank in Same State as Borrower", value=True)
    bank_experience = st.selectbox("Bank SBA Experience", ["High (100+ loans)", "Medium (10–100 loans)", "Low (< 10 loans)"], index=0)
    bank_loans_map = {"High (100+ loans)": 500, "Medium (10–100 loans)": 50, "Low (< 10 loans)": 5}
    bank_prior_loans = bank_loans_map[bank_experience]
    bank_def_rate = st.slider("Bank's Historical Default Rate (%)", min_value=0.0, max_value=25.0, value=8.0, step=0.5)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # --- Assess Button ---
    assess_clicked = st.button("🔍  ASSESS RISK", type="primary", use_container_width=True)


# ============================================================
# Main Content Area
# ============================================================
if assess_clicked:
    # Build input dataframe
    input_data = build_input_df(
        loan_amount, sba_guarantee, term_months, interest_rate,
        jobs_supported, naics_sector, business_type, business_age_val,
        is_franchise, is_variable, is_revolving, has_collateral,
        is_same_state, bank_prior_loans, bank_def_rate
    )

    # Get predictions
    pd_score = model.predict_proba(input_data)[:, 1][0]
    lgd = (loan_amount - sba_guarantee) / loan_amount
    ead = loan_amount
    expected_loss = pd_score * lgd * ead
    unguaranteed = loan_amount - sba_guarantee
    tier_num, tier_label, tier_class, tier_advice = get_risk_tier(pd_score)

    # ---- Tabs ----
    tab1, tab2, tab3 = st.tabs(["📊 Risk Assessment", "🔍 SHAP Explanation", "🔄 What-If Analysis"])

    # ============================================================
    # TAB 1: Risk Assessment
    # ============================================================
    with tab1:
        # Risk Tier Banner
        st.markdown(f'<div class="tier-card {tier_class}">{tier_label}</div>', unsafe_allow_html=True)
        st.caption(f"*{tier_advice}*")

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # Key Metrics Row 1
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric("Default Probability", f"{pd_score:.1%}", "Model predicted PD")
        with c2:
            render_metric("Expected Loss", f"${expected_loss:,.0f}", "PD × LGD × EAD")
        with c3:
            render_metric("Bank Exposure", f"${unguaranteed:,.0f}", f"{lgd:.0%} of loan unguaranteed")
        with c4:
            render_metric("SBA Covers", f"${sba_guarantee:,.0f}", f"{guarantee_pct}% guaranteed")

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # EL Formula Breakdown
        st.markdown("#### 📐 Expected Loss Formula (Basel II/III)")
        f1, f2, f3, f4, f5, f6, f7 = st.columns([2, 0.5, 2, 0.5, 2, 0.5, 2])
        with f1:
            render_metric("PD", f"{pd_score:.2%}", "Probability of Default")
        with f2:
            st.markdown("<div style='text-align:center; font-size:2rem; color:#64748b; padding-top:1.5rem;'>×</div>", unsafe_allow_html=True)
        with f3:
            render_metric("LGD", f"{lgd:.2%}", "Loss Given Default")
        with f4:
            st.markdown("<div style='text-align:center; font-size:2rem; color:#64748b; padding-top:1.5rem;'>×</div>", unsafe_allow_html=True)
        with f5:
            render_metric("EAD", f"${ead:,.0f}", "Exposure at Default")
        with f6:
            st.markdown("<div style='text-align:center; font-size:2rem; color:#64748b; padding-top:1.5rem;'>=</div>", unsafe_allow_html=True)
        with f7:
            render_metric("Expected Loss", f"${expected_loss:,.0f}", "Dollar risk per loan")

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # Loan Summary Table
        st.markdown("#### 📋 Loan Summary")
        summary_data = {
            "Parameter": [
                "Loan Amount", "SBA Guarantee", "Guarantee Ratio",
                "Term", "Interest Rate", "Rate Type",
                "Industry", "Business Age", "Business Type",
                "Franchise", "Collateral", "Jobs Supported",
                "Bank Experience", "Bank Default Rate", "Same-State Lender"
            ],
            "Value": [
                f"${loan_amount:,}", f"${sba_guarantee:,}", f"{guarantee_pct}%",
                f"{term_months} months ({term_months // 12} years)", f"{interest_rate}%",
                "Variable" if is_variable else "Fixed",
                sector_label, business_age, business_type,
                "Yes" if is_franchise else "No",
                "Yes" if has_collateral else "No",
                str(jobs_supported),
                bank_experience, f"{bank_def_rate}%",
                "Yes" if is_same_state else "No"
            ]
        }
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    # ============================================================
    # TAB 2: SHAP Explanation
    # ============================================================
    with tab2:
        st.markdown("#### Why did the model make this decision?")
        st.markdown("The waterfall plot below shows each feature's contribution to the final prediction. "
                     "Red bars push the prediction **toward default**, blue bars push it **away from default**.")

        with st.spinner("Computing SHAP values..."):
            preprocessor = model.named_steps['preprocessor']
            classifier = model.named_steps['classifier']

            input_processed = preprocessor.transform(input_data)
            feature_names = preprocessor.get_feature_names_out()
            input_df = pd.DataFrame(input_processed, columns=feature_names)

            explainer = shap.TreeExplainer(classifier)
            shap_values = explainer(input_df)

            # Waterfall plot
            fig_waterfall, ax = plt.subplots(figsize=(10, 7))
            fig_waterfall.patch.set_facecolor('#0E1117')
            ax.set_facecolor('#0E1117')
            shap.plots.waterfall(shap_values[0], max_display=12, show=False)
            
            # Fix text and axis colors for dark mode
            plt.setp(ax.get_xticklabels(), color='#e2e8f0')
            plt.setp(ax.get_yticklabels(), color='#e2e8f0')
            ax.xaxis.label.set_color('#e2e8f0')
            ax.tick_params(axis='both', colors='#e2e8f0')
            for spine in ax.spines.values():
                spine.set_edgecolor('#475569')

            plt.tight_layout()
            st.pyplot(fig_waterfall)
            plt.close()

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # Top risk drivers summary
        st.markdown("#### 📌 Top Risk Drivers")
        shap_df = pd.DataFrame({
            'Feature': feature_names,
            'SHAP Value': shap_values[0].values
        }).sort_values('SHAP Value', key=abs, ascending=False).head(8)

        risk_drivers = shap_df[shap_df['SHAP Value'] > 0].head(4)
        mitigating = shap_df[shap_df['SHAP Value'] < 0].head(4)

        rd_col, mit_col = st.columns(2)
        with rd_col:
            st.markdown("**🔴 Increasing Risk:**")
            for _, row in risk_drivers.iterrows():
                name = row['Feature'].replace('num__', '').replace('cat__', '').replace('bin__', '')
                st.markdown(f"- `{name}` (+{row['SHAP Value']:.3f})")

        with mit_col:
            st.markdown("**🟢 Reducing Risk:**")
            for _, row in mitigating.iterrows():
                name = row['Feature'].replace('num__', '').replace('cat__', '').replace('bin__', '')
                st.markdown(f"- `{name}` ({row['SHAP Value']:.3f})")

    # ============================================================
    # TAB 3: What-If Analysis
    # ============================================================
    with tab3:
        st.markdown("#### Scenario Analysis: How does changing the guarantee affect expected loss?")
        st.markdown("Adjust the SBA guarantee percentage below to see how it impacts the bank's expected loss.")

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # Generate scenarios for all guarantee levels
        scenarios = []
        for pct in range(50, 95, 5):
            new_sba = loan_amount * (pct / 100)
            new_lgd = (loan_amount - new_sba) / loan_amount
            new_el = pd_score * new_lgd * loan_amount
            new_bank_exposure = loan_amount - new_sba
            scenarios.append({
                'Guarantee %': f"{pct}%",
                'SBA Covers': f"${new_sba:,.0f}",
                'Bank Exposure': f"${new_bank_exposure:,.0f}",
                'LGD': f"{new_lgd:.1%}",
                'Expected Loss': f"${new_el:,.0f}",
            })

        scenario_df = pd.DataFrame(scenarios)
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        # Visual chart
        chart_data = []
        for pct in range(50, 95, 1):
            new_sba = loan_amount * (pct / 100)
            new_lgd = (loan_amount - new_sba) / loan_amount
            new_el = pd_score * new_lgd * loan_amount
            chart_data.append({'Guarantee %': pct, 'Expected Loss ($)': new_el})

        chart_df = pd.DataFrame(chart_data)

        fig_whatif, ax = plt.subplots(figsize=(10, 4))
        fig_whatif.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#1A1D29')
        ax.plot(chart_df['Guarantee %'], chart_df['Expected Loss ($)'], color='#4F8BF9', linewidth=2.5)
        ax.fill_between(chart_df['Guarantee %'], chart_df['Expected Loss ($)'], alpha=0.15, color='#4F8BF9')
        ax.axvline(x=guarantee_pct, color='#ef4444', linestyle='--', linewidth=1.5, label=f'Current ({guarantee_pct}%)')
        ax.set_xlabel('SBA Guarantee %', color='#94a3b8', fontsize=12)
        ax.set_ylabel('Expected Loss ($)', color='#94a3b8', fontsize=12)
        ax.set_title('Expected Loss vs. SBA Guarantee Percentage', color='#f8fafc', fontsize=14, fontweight='bold')
        ax.tick_params(colors='#64748b')
        ax.spines['bottom'].set_color('#334155')
        ax.spines['left'].set_color('#334155')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(facecolor='#1A1D29', edgecolor='#334155', labelcolor='#94a3b8')
        ax.grid(axis='y', alpha=0.15, color='#475569')
        plt.tight_layout()
        st.pyplot(fig_whatif)
        plt.close()

        st.info(f"💡 **Insight:** Increasing the SBA guarantee from {guarantee_pct}% to 90% would reduce the bank's "
                f"expected loss by **{(1 - (10/((100-guarantee_pct) or 1)))*100:.0f}%**, but may increase moral hazard risk.")

else:
    # ============================================================
    # Landing Page (no assessment yet)
    # ============================================================
    st.markdown("")

    # Hero metrics
    hero1, hero2, hero3, hero4 = st.columns(4)
    with hero1:
        render_metric("Training Loans", "456,278", "FY 2010 — FY 2020")
    with hero2:
        render_metric("ROC-AUC", "0.7506", "Risk ranking accuracy")
    with hero3:
        render_metric("PR-AUC", "0.3550", "Default detection power")
    with hero4:
        render_metric("Risk Tiers", "4 Levels", "Green → Red classification")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # How it works
    st.markdown("### How It Works")

    hw1, hw2, hw3, hw4 = st.columns(4)
    with hw1:
        st.markdown("""
        <div class="info-box">
            <h4>📋 Step 1</h4>
            <p style="color:#94a3b8;">Enter loan application details in the sidebar — loan amount, term, industry, borrower profile, and lender information.</p>
        </div>
        """, unsafe_allow_html=True)
    with hw2:
        st.markdown("""
        <div class="info-box">
            <h4>🤖 Step 2</h4>
            <p style="color:#94a3b8;">Our HistGradientBoosting model predicts the Probability of Default (PD) using 19 engineered features.</p>
        </div>
        """, unsafe_allow_html=True)
    with hw3:
        st.markdown("""
        <div class="info-box">
            <h4>💰 Step 3</h4>
            <p style="color:#94a3b8;">The Expected Loss engine calculates dollar risk using Basel II/III: EL = PD × LGD × EAD.</p>
        </div>
        """, unsafe_allow_html=True)
    with hw4:
        st.markdown("""
        <div class="info-box">
            <h4>🔍 Step 4</h4>
            <p style="color:#94a3b8;">SHAP explains exactly why the model made its decision — which features increased or decreased risk.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Model Details
    st.markdown("### About the Model")
    about1, about2 = st.columns(2)

    with about1:
        st.markdown("""
        <div class="info-box">
            <h4>📊 Dataset</h4>
            <p style="color:#94a3b8;">
                <strong>Source:</strong> SBA 7(a) FOIA Data (data.sba.gov)<br>
                <strong>Records:</strong> 514,983 loans (FY2010 – Present)<br>
                <strong>Default Rate:</strong> 8.70%<br>
                <strong>Split:</strong> Temporal — Train (2010–2020), Test (2021–2026)
            </p>
        </div>
        """, unsafe_allow_html=True)

    with about2:
        st.markdown("""
        <div class="info-box">
            <h4>⚙️ Technical Details</h4>
            <p style="color:#94a3b8;">
                <strong>Algorithm:</strong> HistGradientBoosting (scikit-learn)<br>
                <strong>Features:</strong> 19 engineered (leak-safe bank & sector rates)<br>
                <strong>Class Balance:</strong> Balanced class weights<br>
                <strong>Explainability:</strong> SHAP TreeExplainer
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Key Findings
    st.markdown("### 🔬 Key Research Findings")
    kf1, kf2, kf3 = st.columns(3)
    with kf1:
        st.markdown("""
        <div class="info-box">
            <h4>📈 Moral Hazard</h4>
            <p style="color:#94a3b8;">Loans with 85% SBA guarantee have a <strong>13.1% default rate</strong> vs 7.8% for 75% guarantee loans. Higher guarantees correlate with laxer underwriting.</p>
        </div>
        """, unsafe_allow_html=True)
    with kf2:
        st.markdown("""
        <div class="info-box">
            <h4>📉 Fed Rate Impact</h4>
            <p style="color:#94a3b8;">Default rates spiked from ~8% to <strong>24% in 2023</strong> following Federal Reserve rate hikes, devastating variable-rate SBA borrowers.</p>
        </div>
        """, unsafe_allow_html=True)
    with kf3:
        st.markdown("""
        <div class="info-box">
            <h4>🏪 Industry Risk</h4>
            <p style="color:#94a3b8;">Retail (45) and Transportation (48) have the highest default rates at <strong>~11.5%</strong>, while Management (55) is safest at <strong>3.4%</strong>.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown('<p style="text-align:center; color:#475569; font-size:0.85rem;">Built with ❤️ using Python, scikit-learn, SHAP & Streamlit</p>', unsafe_allow_html=True)
