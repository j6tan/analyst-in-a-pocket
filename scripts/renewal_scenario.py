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
    st.switch_page("scripts/home.py")
st.divider()

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL ---
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

# --- 3. PERSISTENCE & INITIALIZATION ---
if 'renewal_analysis' not in st.session_state.app_db:
    st.session_state.app_db['renewal_analysis'] = {}
ren_data = st.session_state.app_db['renewal_analysis']

if 'initialized' not in ren_data:
    ren_data.update({
        "mortgage_bal": float(prof.get('m_bal', 500000.0)),
        "remaining_amort": float(prof.get('m_amort', 25)),
        "fixed_rate_offer": float(intel['rates'].get('five_year_fixed_uninsured', 4.26)),
        "var_rate_start": float(intel['rates'].get('five_year_variable', 5.50)),
        "target_rate": 3.50,
        "months_to_target": 24.0,
        "term_months": 60,
        "initialized": True
    })

# --- 4. HEADER ---
st.title("The Renewal Dilemma")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📝 Strategic Brief: {household}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        Compare the certainty of a <b>Fixed Rate</b> against the potential of a <b>Variable Path</b>. 
        This tool models your expected rate trajectory to see which choice builds more equity.
    </p>
    <p style="color: #6c757d; font-size: 0.85em; margin-top: 10px; font-style: italic;">
        Note: Balance and amortization are pulled from your Profile. Market rates are fetched from Intel.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. CORE INPUTS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Mortgage Details")
    m_bal = cloud_input("Current Mortgage Balance ($)", "renewal_analysis", "mortgage_bal", step=5000.0)
    m_amort = cloud_input("Remaining Amortization (Years)", "renewal_analysis", "remaining_amort", step=1.0)
    
    term_options = [1,2,3,4,5]
    curr_term_yrs = int(ren_data.get('term_months', 60) / 12)
    m_term_yr = st.selectbox("Renewal Term (Years)", term_options, 
                             index=term_options.index(curr_term_yrs) if curr_term_yrs in term_options else 4,
                             key="renewal_analysis:term_months_sel", on_change=sync_widget, args=("renewal_analysis:term_months_sel",))
    ren_data['term_months'] = m_term_yr * 12

with col2:
    st.subheader("📉 Your Market Outlook")
    fixed_offer = cloud_input("Contracted Fixed Rate (%)", "renewal_analysis", "fixed_rate_offer", step=0.05)
    var_start = cloud_input("Current Variable Rate (%)", "renewal_analysis", "var_rate_start", step=0.05)
    
    st.write("---")
    target_r = cloud_input("Target Variable Rate (%)", "renewal_analysis", "target_rate", step=0.1)
    target_mo = cloud_input("Months to reach Target", "renewal_analysis", "months_to_target", step=1.0)

# --- 6. CALCULATIONS ---
months = int(ren_data['term_months'])
fixed_mo = (fixed_offer / 100) / 12
pmt_fixed = (m_bal * fixed_mo) / (1 - (1 + fixed_mo)**-(m_amort * 12))

# Variable Path Logic: Linear progression to target, then hold
var_rates = []
start_r = var_start / 100
end_r = target_r / 100
total_drop = start_r - end_r
monthly_drop = total_drop / target_mo if target_mo > 0 else 0

for m in range(months):
    if m < target_mo:
        current_step_rate = start_r - (monthly_drop * m)
    else:
        current_step_rate = end_r
    var_rates.append(max(0.005, current_step_rate))

# Amortization Simulation
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
    # Recalculate pmt each month for variable to simulate actual bank behavior
    pmt_var = (v_bal * v_mo_rate) / (1 - (1 + v_mo_rate)**-((m_amort * 12) - m + 1))
    v_int = v_bal * v_mo_rate
    v_prin = pmt_var - v_int
    v_bal -= v_prin
    v_int_total += v_int
    
    data_rows.append({
        "Month": m, "V_Rate": var_rates[m-1] * 100, "V_Pmt": pmt_var, 
        "V_Int": v_int, "F_Pmt": pmt_fixed, "F_Int": f_int,
        "Cum_V_Int": v_int_total, "Cum_F_Int": f_int_total
    })

df = pd.DataFrame(data_rows)
savings = f_int_total - v_int_total

# --- 7. RESULTS ---
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
    st.metric("Final Variable Rate", f"{target_r:.2f}%")

# --- 8. GRAPHS (Fixed ValueError by using ticksuffix) ---
tab1, tab2, tab3 = st.tabs(["Rate Trajectory", "Payment Comparison", "Interest Burn"])

with tab1:
    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=df["V_Rate"], name="Variable Path", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=[fixed_offer]*months, name="Fixed Rate", line=dict(color=CHARCOAL, dash='dash')))
    fig_rate.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig_rate.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_rate, use_container_width=True)

with tab2:
    fig_pmt = go.Figure()
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=df["V_Pmt"], name="Variable Payment", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=df["F_Pmt"], name="Fixed Payment", line=dict(color=CHARCOAL, dash='dash')))
    fig_pmt.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig_pmt.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_pmt, use_container_width=True)

with tab3:
    fig_int = go.Figure()
    fig_int.add_trace(go.Scatter(x=df["Month"], y=df["Cum_V_Int"], name="Total Variable Interest", fill='tozeroy', line=dict(color=PRIMARY_GOLD)))
    fig_int.add_trace(go.Scatter(x=df["Month"], y=df["Cum_F_Int"], name="Total Fixed Interest", line=dict(color=CHARCOAL, width=2)))
    fig_int.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig_int.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_int, use_container_width=True)

show_disclaimer()
