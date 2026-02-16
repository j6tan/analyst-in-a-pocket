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

# --- 2. DATA RETRIEVAL ---
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_variable": 5.50, "five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()
prof = st.session_state.app_db.get('profile', {})
household = f"{prof.get('p1_name', 'Client')} & {prof.get('p2_name', '')}".strip(" & ")

# --- 3. PERSISTENCE ---
if 'renewal_analysis' not in st.session_state.app_db:
    st.session_state.app_db['renewal_analysis'] = {}
ren_data = st.session_state.app_db['renewal_analysis']

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
<div style="background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD};">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0;">📋 Strategic Brief: {household}</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; margin-bottom: 0;">
        Compare the <b>Fixed Path</b> (Certainty) against your projected <b>Variable Path</b> (Opportunity). 
        Use the Stress Test to see the cost of the "Stay-High" scenario.
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")

# --- 5. INPUTS ---
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
    
    fixed_rate = cloud_input("Contracted Fixed Rate (%)", "renewal_analysis", "fixed_rate", step=0.05)

with col2:
    st.subheader("📉 Your Market Outlook")
    curr_var_rate = cloud_input("Current Variable Rate (%)", "renewal_analysis", "curr_var_rate", step=0.05)
    
    # DIVIDER REMOVED AS REQUESTED
    target_var_rate = cloud_input("Target Variable Rate (%)", "renewal_analysis", "target_var_rate", step=0.05)
    months_to_target = cloud_input("Months to reach Target", "renewal_analysis", "months_to_target", step=1.0)
    
    st.write("")
    worst_case = st.toggle("🔥 Stress Test: 'Stay-High' Scenario", help="Simulates variable rates never dropping from current levels.")

# --- 6. CALCULATIONS ---
term_months = int(ren_data['term_yrs'] * 12)
fixed_mo = (fixed_rate / 100) / 12
pmt_fixed = (m_bal * fixed_mo) / (1 - (1 + fixed_mo)**-(m_amort * 12))

# Variable Simulation Logic
start_v = curr_var_rate / 100
end_v = (curr_var_rate / 100) if worst_case else (target_var_rate / 100)
mo_drop = (start_v - end_v) / months_to_target if (months_to_target > 0 and not worst_case) else 0

v_bal, f_bal, v_int_total, f_int_total = m_bal, m_bal, 0, 0
data_rows = []

for m in range(1, term_months + 1):
    # Fixed Path
    f_int = f_bal * fixed_mo
    f_prin = pmt_fixed - f_int
    f_bal -= f_prin
    f_int_total += f_int
    
    # Variable Path (Linear drop then hold)
    if worst_case:
        curr_v_rate = start_v
    else:
        curr_v_rate = start_v - (mo_drop * (m-1)) if m <= months_to_target else end_v
        
    v_mo_rate = max(0.005, curr_v_rate) / 12
    pmt_var = (v_bal * v_mo_rate) / (1 - (1 + v_mo_rate)**-((m_amort * 12) - m + 1))
    v_int = v_bal * v_mo_rate
    v_prin = pmt_var - v_int
    v_bal -= v_prin
    v_int_total += v_int
    
    data_rows.append({"Month": m, "V_Rate": curr_v_rate*100, "V_Pmt": pmt_var, "F_Pmt": pmt_fixed, "Cum_V_Int": v_int_total, "Cum_F_Int": f_int_total})

df = pd.DataFrame(data_rows)
interest_diff = f_int_total - v_int_total

# --- 7. EXECUTIVE SUMMARY ---
st.divider()
st.subheader(f"📊 The Verdict: {ren_data['term_yrs']}-Year Horizon")

v1, v2, v3 = st.columns(3)
with v1:
    st.metric("Total Fixed Interest", f"${f_int_total:,.0f}")
with v2:
    label = "Interest Savings" if interest_diff > 0 else "Interest Penalty"
    st.metric(f"Variable {label}", f"${abs(interest_diff):,.0f}", 
              delta="Better" if interest_diff > 0 else "Worse", 
              delta_color="normal" if interest_diff > 0 else "inverse")
with v3:
    cuts_needed = (curr_var_rate - fixed_rate) / 0.25
    st.metric("Break-Even Cuts", f"{cuts_needed:.1f} cuts", help="Number of 0.25% cuts needed to match the fixed rate.")



# --- 8. VISUALS ---
tab1, tab2, tab3 = st.tabs(["Rate Trajectory", "Payment Comparison", "Interest Burn"])
with tab1:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df["Month"], y=df["V_Rate"], name="Variable Path", line=dict(color=PRIMARY_GOLD, width=3)))
    fig1.add_trace(go.Scatter(x=df["Month"], y=[fixed_rate]*term_months, name="Fixed Rate", line=dict(color=CHARCOAL, dash='dash')))
    fig1.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig1.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["Month"], y=df["V_Pmt"], name="Variable Payment", line=dict(color=PRIMARY_GOLD, width=3)))
    fig2.add_trace(go.Scatter(x=df["Month"], y=[pmt_fixed]*term_months, name="Fixed Payment", line=dict(color=CHARCOAL, dash='dash')))
    fig2.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig2.update_yaxes(tickprefix="$")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["Month"], y=df["Cum_V_Int"], name="Variable Interest", fill='tozeroy', line=dict(color=PRIMARY_GOLD)))
    fig3.add_trace(go.Scatter(x=df["Month"], y=df["Cum_F_Int"], name="Fixed Interest", line=dict(color=CHARCOAL, width=2)))
    fig3.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20))
    fig3.update_yaxes(tickprefix="$")
    st.plotly_chart(fig3, use_container_width=True)

show_disclaimer()
