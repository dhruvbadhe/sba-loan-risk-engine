"""
SBA Loan Risk Assessment Engine — Streamlit App (Decoupled API Frontend)
================================================
A production-grade credit risk assessment tool for SBA 7(a) loan officers.
Communicates directly with the deployed FastAPI backend.
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
import shap

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

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }

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
# Constants
# ============================================================
API_BASE_URL = "https://sba-loan-risk-api.onrender.com"

# Emojis mapped to sectors
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

SECTOR_DEFAULT_RATES = {
    '11': 0.053, '21': 0.073, '22': 0.058, '23': 0.095,
    '31': 0.088, '32': 0.088, '33': 0.088, '42': 0.087,
    '44': 0.115, '45': 0.115, '48': 0.115, '49': 0.102,
    '51': 0.089, '52': 0.058, '53': 0.073, '54': 0.078,
    '55': 0.034, '56': 0.090, '61': 0.091, '62': 0.058,
    '71': 0.111, '72': 0.094, '81': 0.088, '92': 0.089,
}

# ============================================================
# Helpers
# ============================================================
def render_metric(label, value, sub=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def get_risk_tier(pd_score):
    if pd_score < 0.10:
        return 1, '🟢 TIER 1 — AUTO APPROVE', 'tier-1', 'Low risk. Standard processing recommended.'
    elif pd_score < 0.25:
        return 2, '🟡 TIER 2 — MANUAL REVIEW', 'tier-2', 'Moderate risk. Manual underwriting review recommended.'
    elif pd_score < 0.40:
        return 3, '🟠 TIER 3 — SENIOR REVIEW', 'tier-3', 'Elevated risk. Senior credit officer review + additional collateral required.'
    else:
        return 4, '🔴 TIER 4 — RECOMMEND DENIAL', 'tier-4', 'High risk. Recommend denial or significant restructuring of loan terms.'

# ============================================================
# Session State Authentication Check
# ============================================================
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

# Logout Action
def logout():
    st.session_state["access_token"] = None
    st.rerun()

# --- LOGIN PAGE ---
if st.session_state["access_token"] is None:
    st.markdown("<h2 style='text-align:center; padding-top: 3rem;'>🏦 SBA Loan Risk Portal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94a3b8;'>Please sign in to access the Underwriting Engine</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='info-box'>", unsafe_allow_html=True)
        login_username = st.text_input("Username")
        login_password = st.text_input("Password", type="password")
        login_button = st.button("Sign In", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if login_button:
            with st.spinner("Authenticating..."):
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/login",
                        data={"username": login_username, "password": login_password},
                        timeout=30.0
                    )
                    if res.status_code == 200:
                        st.session_state["access_token"] = res.json()["access_token"]
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception as e:
                    st.error(f"Cannot connect to auth server: {e}")
    st.stop()

# --- MAIN DASHBOARD (Authenticated) ---
st.markdown("""
<div class="main-header">
    <h1>🏦 SBA Loan Risk Assessment Engine</h1>
    <p>Predict default probability • Calculate expected dollar loss • Explain risk drivers</p>
</div>
""", unsafe_allow_html=True)

# Add logout hook via button
if st.button("🔒 Log Out", type="secondary"):
    logout()

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
    st.markdown("### ### Lender Information")
    is_same_state = st.toggle("Bank in Same State as Borrower", value=True)
    bank_experience = st.selectbox("Bank SBA Experience", ["High (100+ loans)", "Medium (10–100 loans)", "Low (< 10 loans)"], index=0)
    bank_loans_map = {"High (100+ loans)": 500, "Medium (10–100 loans)": 50, "Low (< 10 loans)": 5}
    bank_prior_loans = bank_loans_map[bank_experience]
    bank_def_rate = st.slider("Bank's Historical Default Rate (%)", min_value=0.0, max_value=25.0, value=8.0, step=0.5)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    assess_clicked = st.button("🔍  ASSESS RISK", type="primary", use_container_width=True)

# ============================================================
# Main Processing Logic (API Interaction)
# ============================================================
if assess_clicked:
    # Build payload matching FastAPI schema
    payload = {
        "grossapproval": float(loan_amount),
        "sbaguaranteedapproval": float(sba_guarantee),
        "terminmonths": int(term_months),
        "initialinterestrate": float(interest_rate),
        "jobssupported": int(jobs_supported),
        "bank_prior_def_rate": float(bank_def_rate / 100.0),
        "bank_prior_loans": float(bank_prior_loans),
        "sector_historical_default_rate": float(SECTOR_DEFAULT_RATES.get(naics_sector, 0.087)),
        "naics_sector": naics_sector,
        "businesstype": business_type,
        "business_age_group": business_age_val,
        "bank_experience_tier": "High" if bank_prior_loans >= 100 else ("Medium" if bank_prior_loans >= 10 else "Low"),
        "revolverstatus": 1 if is_revolving else 0,
        "is_same_state_bank": 1 if is_same_state else 0,
        "is_variable_rate": 1 if is_variable else 0,
        "is_franchise": 1 if is_franchise else 0,
        "collateralind": 1 if has_collateral else 0
    }

    with st.spinner("Analyzing risk parameters via FastAPI..."):
        try:
            # Call live API with JWT Token in Header
            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
            res = requests.post(f"{API_BASE_URL}/predict", json=payload, headers=headers, timeout=10.0)
            
            if res.status_code == 200:
                result = res.json()
                pd_score = result["probability_of_default"]
                lgd = result["loss_given_default"]
                ead = result["exposure_at_default"]
                expected_loss = result["expected_loss"]
                tier_label = result["risk_tier"]
                action = result["underwriting_action"]
                
                # Fetch SHAP data from API
                shap_base_value = result["shap_base_value"]
                shap_contributions = result["shap_values"]
                processed_features = result["processed_features"]
                
                # Dynamic risk properties mapping
                _, _, tier_class, tier_advice = get_risk_tier(pd_score)
                unguaranteed = loan_amount - sba_guarantee

                # ---- Render Tabs ----
                tab1, tab2, tab3 = st.tabs(["📊 Risk Assessment", "🔍 SHAP Explanation", "🔄 What-If Analysis"])

                # --- Tab 1: Risk Metrics ---
                with tab1:
                    st.markdown(f'<div class="tier-card {tier_class}">{action} ({tier_label})</div>', unsafe_allow_html=True)
                    st.caption(f"*{tier_advice}*")
                    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

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
                        render_metric("Expected Loss", f"${expected_loss:,.0f}", "Risk Cost per Loan")

                # --- Tab 2: SHAP explanations (Reconstructed Locally) ---
                with tab2:
                    st.markdown("#### Why did the model make this decision?")
                    st.markdown("The waterfall plot below is reconstructed directly from your Render API response metadata. "
                                 "Red bars increase default risk; blue bars decrease risk.")

                    # Reconstruct a shap.Explanation object in memory from the API JSON data
                    sorted_features = sorted(shap_contributions.keys())
                    vals = np.array([shap_contributions[f] for f in sorted_features])
                    data = np.array([processed_features[f] for f in sorted_features])
                    
                    explanation = shap.Explanation(
                        values=vals,
                        base_values=shap_base_value,
                        data=data,
                        feature_names=sorted_features
                    )

                    fig_waterfall, ax = plt.subplots(figsize=(10, 7))
                    fig_waterfall.patch.set_facecolor('#0E1117')
                    ax.set_facecolor('#0E1117')
                    shap.plots.waterfall(explanation, max_display=12, show=False)
                    
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
                    st.markdown("#### 📌 Top Risk Drivers")
                    
                    drivers_list = sorted(shap_contributions.items(), key=lambda x: x[1], reverse=True)
                    
                    rd_col, mit_col = st.columns(2)
                    with rd_col:
                        st.markdown("**🔴 Increasing Risk:**")
                        for name, val in drivers_list[:4]:
                            if val > 0:
                                clean_name = name.replace('num__', '').replace('cat__', '').replace('bin__', '')
                                st.markdown(f"- `{clean_name}` (+{val:.3f})")
                    with mit_col:
                        st.markdown("**🟢 Reducing Risk:**")
                        for name, val in reversed(drivers_list):
                            if val < 0:
                                clean_name = name.replace('num__', '').replace('cat__', '').replace('bin__', '')
                                st.markdown(f"- `{clean_name}` ({val:.3f})")
                                if len(mit_col.children) >= 5:
                                    break

                # --- Tab 3: What-If Analysis ---
                with tab3:
                    st.markdown("#### Scenario Analysis: How does guarantee affect expected loss?")
                    
                    scenarios = []
                    for pct in range(50, 95, 5):
                        new_sba = loan_amount * (pct / 100)
                        new_lgd = (loan_amount - new_sba) / loan_amount
                        new_el = pd_score * new_lgd * loan_amount
                        scenarios.append({
                            "Guarantee %": f"{pct}%",
                            "SBA Covers": f"${new_sba:,.0f}",
                            "Bank Exposure": f"${(loan_amount - new_sba):,.0f}",
                            "LGD": f"{new_lgd:.1%}",
                            "Expected Loss": f"${new_el:,.0f}",
                        })
                    st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)

                    chart_data = []
                    for pct in range(50, 95, 1):
                        new_sba = loan_amount * (pct / 100)
                        new_lgd = (loan_amount - new_sba) / loan_amount
                        chart_data.append({'Guarantee %': pct, 'Expected Loss ($)': pd_score * new_lgd * loan_amount})
                    chart_df = pd.DataFrame(chart_data)

                    fig_whatif, ax = plt.subplots(figsize=(10, 4))
                    fig_whatif.patch.set_facecolor('#0E1117')
                    ax.set_facecolor('#1A1D29')
                    ax.plot(chart_df['Guarantee %'], chart_df['Expected Loss ($)'], color='#4F8BF9', linewidth=2.5)
                    ax.fill_between(chart_df['Guarantee %'], chart_df['Expected Loss ($)'], alpha=0.15, color='#4F8BF9')
                    ax.axvline(x=guarantee_pct, color='#ef4444', linestyle='--', label=f'Current ({guarantee_pct}%)')
                    ax.set_xlabel('SBA Guarantee %', color='#94a3b8')
                    ax.set_ylabel('Expected Loss ($)', color='#94a3b8')
                    ax.set_title('Expected Loss vs. SBA Guarantee Percentage', color='#f8fafc', fontweight='bold')
                    ax.tick_params(colors='#64748b')
                    ax.spines['bottom'].set_color('#334155')
                    ax.spines['left'].set_color('#334155')
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.legend(facecolor='#1A1D29', labelcolor='#94a3b8')
                    ax.grid(axis='y', alpha=0.15, color='#475569')
                    plt.tight_layout()
                    st.pyplot(fig_whatif)
                    plt.close()

            else:
                st.error(f"Prediction server returned an error: {res.status_code}. Detail: {res.text}")
        except Exception as e:
            st.error(f"Failed to communicate with prediction API. Ensure backend is running. Error: {e}")

else:
    # --- Landing Hero metrics ---
    st.markdown("")
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
    st.markdown("### How It Works")
    hw1, hw2, hw3, hw4 = st.columns(4)
    with hw1:
        st.markdown("<div class='info-box'><h4>📋 Step 1</h4><p style='color:#94a3b8;'>Enter loan application details in the sidebar.</p></div>", unsafe_allow_html=True)
    with hw2:
        st.markdown("<div class='info-box'><h4>🤖 Step 2</h4><p style='color:#94a3b8;'>Our HistGradientBoosting model predicts the Default Probability (PD) via FastAPI.</p></div>", unsafe_allow_html=True)
    with hw3:
        st.markdown("<div class='info-box'><h4>💰 Step 3</h4><p style='color:#94a3b8;'>Basel Expected Loss formula calculates dollar risk: EL = PD × LGD × EAD.</p></div>", unsafe_allow_html=True)
    with hw4:
        st.markdown("<div class='info-box'><h4>🔍 Step 4</h4><p style='color:#94a3b8;'>SHAP returns explainability metrics dynamically from the backend.</p></div>", unsafe_allow_html=True)
