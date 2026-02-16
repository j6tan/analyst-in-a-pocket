import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import json
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject the Wealthsimple-inspired Editorial CSS
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

# --- 2. DATA RETRIEVAL (DYNAMIC LINKING) ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_variable": 5.50, "five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()
prof = st.session_state.app_db.get('profile', {}) # Link to main app_db
name1 = prof.get('p1_name', 'Client')
name2 = prof.get('p2_name', '')
household = f"{name1} & {name2}" if name2 else name1

# --- 3. PERSISTENCE ---
if 'renewal_analysis' not in st.session_state.app_db:
    st.session_state.app_db['renewal_analysis'] = {}
ren_data = st.session_state.app_db['renewal_analysis']

# Force initial values from Profile and Intel if not already set
if 'initialized' not in ren_data:
    ren_data.update({
        "m_bal": float(prof.get('m_bal', 500000.0)),
        "m_amort": float(prof.get('m_amort', 25.0)),
        "fixed_rate": float(intel['rates'].get('five_year_fixed_uninsured', 4.26)),
        "curr_var_rate": float(intel['rates'].get('five_year_variable', 5.50)),
        "target_var_rate": 3.50,
        "months_to_target": 24.0,
        "term_yrs": 5,
        "initialized": True
    })

# --- 4. HEADER ---
st.title("The Renewal Dilemma")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📝 Strategic Brief: {household}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        Your mortgage renewal is a pivotal wealth-decision. This tool models the path between <b>Fixed certainty</b> 
        and <b>Variable opportunity</b>, accounting for your specific market outlook.
    </p>
    <p style="color: #6c757d; font-size: 0.85em; margin-top: 10px; font-style: italic;">
        Note: Balance and amortization are pulled from your Profile. Market rates are fetched from Intel.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS (LAYOUT RESTORED) ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Mortgage Details")
    m_bal = cloud_input("Current Mortgage Balance ($)", "renewal_analysis", "m_bal", step=5000.0)
    m_amort = cloud_input("Remaining Amortization (Years)", "renewal_analysis", "m_amort", step=1.0)
    
    term_options = [1, 2, 3, 4, 5]
    sel_term = st.selectbox("Renewal Term (Years)", term_options, 
                            index=term_options.index(int(ren_data.get('term_yrs', 5))),
                            key="renewal_analysis:term_yrs_sel", on_change=sync_widget, args=("renewal_analysis:term_yrs_sel",))
    ren_data['term_yrs'] = sel_term

with col2:
    st.subheader("📉 Your Market Outlook")
    fixed_rate = cloud_input("Contracted Fixed Rate (%)", "renewal_analysis", "fixed_rate", step=0.05)
    curr_var_rate = cloud_input("Current Variable Rate (%)", "renewal_analysis", "curr_var_rate", step=0.05)
    
    st.markdown("---")
    target_var_rate = cloud_input("Target Variable Rate (%)", "renewal_analysis", "target_var_rate", step=0.05)
    months_to_target = cloud_input("Months to reach Target", "renewal_analysis", "months_to_target", step=1.0)

# --- 6. CALCULATIONS ---
term_months = int(ren_data['term_yrs'] * 12)
fixed_mo_rate = (fixed_rate / 100) / 12
pmt_fixed = (m_bal * fixed_mo_rate) / (1 - (1 + fixed_mo_rate)**-(m_amort * 12))

# Variable Path Simulation
var_rates = []
start_v = curr_var_rate / 100
end_v = target_var_rate / 100
total_drop = start_v - end_v
mo_drop = total_drop / months_to_target if months_to_target > 0 else 0

for m in range(term_months):
    if m < months_to_target:
        current_v = start_v - (mo_drop * m)
    else:
        current_v = end_v
    var_rates.append(max(0.005, current_v))

# Amortization Table
v_bal, f_bal = m_bal, m_bal
v_int_total, f_int_total = 0, 0
data_rows = []

for m in range(1, term_months + 1):
    # Fixed Path
    f_int = f_bal * fixed_mo_rate
    f_prin = pmt_fixed - f_int
    f_bal -= f_prin
    f_int_total += f_int
    
    # Variable Path (Payment recalculated monthly)
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
        "F_Pmt": pmt_fixed,
        "Cum_V_Int": v_int_total,
        "Cum_F_Int": f_int_total
    })

df = pd.DataFrame(data_rows)
savings = f_int_total - v_int_total

# --- 7. EXECUTIVE SUMMARY ---
st.divider()
st.subheader(f"📊 The Verdict: {ren_data['term_yrs']}-Year Horizon")

v1, v2, v3 = st.columns(3)
with v1:
    st.metric("Total Fixed Interest", f"${f_int_total:,.0f}")
with v2:
    st.metric("Total Variable Interest", f"${v_int_total:,.0f}", 
              delta=f"-${savings:,.0f} Savings" if savings > 0 else f"${abs(savings):,.0f} Extra Cost",
              delta_color="normal" if savings > 0 else "inverse")
with v3:
    st.metric("Final Variable Rate", f"{target_var_rate:.2f}%")

# --- 8. VISUAL ANALYSIS ---
tab1, tab2, tab3 = st.tabs(["Rate Trajectory", "Payment Comparison", "Interest Burn"])

with tab1:
    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=df["V_Rate"], name="Variable Path", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=[fixed_rate]*term_months, name="Fixed Rate", line=dict(color=CHARCOAL, dash='dash')))
    fig_rate.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig_rate.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_rate, use_container_width=True)

with tab2:
    fig_pmt = go.Figure()
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=df["V_Pmt"], name="Variable Payment", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_pmt.add_trace(go.Scatter(x=df["Month"], y=[pmt_fixed]*term_months, name="Fixed Payment", line=dict(color=CHARCOAL, dash='dash')))
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
