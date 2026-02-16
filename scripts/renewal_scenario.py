import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import json
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL (MARKET INTEL & PROFILE) ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_variable": 5.50, "five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name', 'Client')
name2 = prof.get('p2_name', '')
household = f"{name1} & {name2}" if name2 else name1

# --- 3. PERSISTENCE ---
if 'renewal_analysis' not in st.session_state.app_db:
    st.session_state.app_db['renewal_analysis'] = {}
ren_data = st.session_state.app_db['renewal_analysis']

# --- 4. INITIALIZATION (PULLING FROM SOURCES) ---
# We force sync these to the profile and intel data on first load
if 'initialized' not in ren_data:
    ren_data.update({
        "mortgage_bal": float(prof.get('m_bal', 500000.0)),
        "remaining_amort": int(prof.get('m_amort', 25)),
        "fixed_rate_offer": float(intel['rates'].get('five_year_fixed_uninsured', 4.26)),
        "var_rate_start": float(intel['rates'].get('five_year_variable', 5.50)),
        "term_months": 60,
        "scenario_cuts": 4,
        "initialized": True
    })

# --- 5. HEADER ---
st.title("The Renewal Dilemma")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📝 Strategic Brief: {household}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        Your mortgage renewal is a pivotal wealth-decision. This tool models the path between <b>Fixed certainty</b> 
        and <b>Variable opportunity</b>, accounting for projected Bank of Canada rate cuts.
    </p>
    <p style="color: #6c757d; font-size: 0.85em; margin-top: 10px; font-style: italic;">
        Note: Remaining balance and amortization are synced from your Profile. Rates are fetched from current Market Intel.
    </p>
</div>
""", unsafe_allow_html=True)



# --- 6. CORE INPUTS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Mortgage Details")
    m_bal = cloud_input("Current Mortgage Balance ($)", "renewal_analysis", "mortgage_bal", step=5000.0)
    m_amort = cloud_input("Remaining Amortization (Years)", "renewal_analysis", "remaining_amort", step=1.0)
    
    # Handle Selectbox persistence for Term
    term_options = [1,2,3,4,5]
    current_term_yrs = int(ren_data.get('term_months', 60) / 12)
    m_term_yr = st.selectbox("Renewal Term (Years)", term_options, 
                             index=term_options.index(current_term_yrs) if current_term_yrs in term_options else 4,
                             key="renewal_analysis:term_months_sel", on_change=sync_widget, args=("renewal_analysis:term_months_sel",))
    ren_data['term_months'] = m_term_yr * 12

with col2:
    st.subheader("📉 Rate Scenarios")
    fixed_offer = cloud_input("Fixed Rate Offer (%)", "renewal_analysis", "fixed_rate_offer", step=0.05)
    var_start = cloud_input("Current Variable Rate (%)", "renewal_analysis", "var_rate_start", step=0.05)
    cuts = st.slider("Total Projected Rate Cuts (0.25% each)", 0, 12, int(ren_data.get('scenario_cuts', 4)), 
                     key="renewal_analysis:scenario_cuts", on_change=sync_widget, args=("renewal_analysis:scenario_cuts",))

# --- 7. CALCULATIONS ---
months = int(ren_data['term_months'])
fixed_mo = (fixed_offer / 100) / 12
pmt_fixed = (m_bal * fixed_mo) / (1 - (1 + fixed_mo)**-(m_amort * 12))

# Variable Path Simulation
cut_size = 0.0025
mo_cut = (cuts * cut_size) / months # Spread cuts linearly over the term

var_rates = []
curr_v = var_start / 100
for m in range(months):
    var_rates.append(max(0.01, curr_v))
    curr_v -= mo_cut

# Build Amortization for both
v_bal, f_bal = m_bal, m_bal
v_int_total, f_int_total = 0, 0
data_rows = []

for m in range(1, months + 1):
    # Fixed
    f_int = f_bal * fixed_mo
    f_prin = pmt_fixed - f_int
    f_bal -= f_prin
    f_int_total += f_int
    
    # Variable
    v_mo_rate = var_rates[m-1] / 12
    pmt_var = (v_bal * v_mo_rate) / (1 - (1 + v_mo_rate)**-((m_amort * 12) - m + 1))
    v_int = v_bal * v_mo_rate
    v_prin = pmt_var - v_int
    v_bal -= v_prin
    v_int_total += v_int
    
    data_rows.append({
        "Month": m,
        "V_Rate": var_rates[m-1] * 100,
        "V_Pmt": pmt_var,
        "V_Int": v_int,
        "F_Pmt": pmt_fixed,
        "F_Int": f_int,
        "Cum_V_Int": v_int_total,
        "Cum_F_Int": f_int_total
    })

df = pd.DataFrame(data_rows)
savings = f_int_total - v_int_total

# --- 8. EXECUTIVE SUMMARY ---
st.divider()
st.subheader(f"📊 The Verdict: {m_term_yr}-Year Horizon")

v1, v2, v3 = st.columns(3)
with v1:
    st.metric("Total Fixed Interest", f"${f_int_total:,.0f}")
with v2:
    st.metric("Total Variable Interest", f"${v_int_total:,.0f}", 
              delta=f"-${savings:,.0f} Savings" if savings > 0 else f"${abs(savings):,.0f} Extra Cost",
              delta_color="normal" if savings > 0 else "inverse")
with v3:
    break_even_cuts = (var_start - fixed_offer) / 0.25
    st.metric("Required Cuts to Break Even", f"{break_even_cuts:.1f} cuts")

# --- 9. VISUAL ANALYSIS ---
tab1, tab2, tab3 = st.tabs(["Rate Path", "Payment Comparison", "Interest Burn"])

with tab1:
    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=df["V_Rate"], name="Variable Path", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=[fixed_offer]*months, name="Fixed Offer", line=dict(color=CHARCOAL, dash='dash')))
    fig_rate.update_layout(plot_bgcolor="white", height=350, yaxis_suffix="%", margin=dict(t=20, b=20))
    st.plotly_chart(fig_rate, use_container_width=True)

with tab2:
    fig_pmt = go.Figure()
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=df["V_Pmt"], name="Variable Payment", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=df["F_Pmt"], name="Fixed Payment", line=dict(color=CHARCOAL, dash='dash')))
    fig_pmt.update_layout(plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"), margin=dict(t=20, b=20))
    st.plotly_chart(fig_pmt, use_container_width=True)

with tab3:
    fig_int = go.Figure()
    fig_int.add_trace(go.Scatter(x=df["Month"], y=df["Cum_V_Int"], name="Total Var Interest", fill='tozeroy', line=dict(color=PRIMARY_GOLD)))
    fig_int.add_trace(go.Scatter(x=df["Month"], y=df["Cum_F_Int"], name="Total Fixed Interest", line=dict(color=CHARCOAL, width=2)))
    fig_int.update_layout(plot_bgcolor="white", height=350, yaxis=dict(tickprefix="$"), margin=dict(t=20, b=20))
    st.plotly_chart(fig_int, use_container_width=True)

show_disclaimer()

