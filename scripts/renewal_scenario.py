import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import base64
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
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_variable": 5.50, "five_year_fixed_uninsured": 4.79}}

intel = load_market_intel()
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name', 'Client')
name2 = prof.get('p2_name', '')
household = f"{name1} & {name2}" if name2 else name1

# --- 3. PERSISTENCE & INITIALIZATION ---
if "renewal_analysis" not in st.session_state.app_db:
    st.session_state.app_db['renewal_analysis'] = {}

ren_store = st.session_state.app_db['renewal_analysis']

if not ren_store.get('initialized'):
    ren_store.update({
        "balance": float(prof.get('m_bal', 500000.0)),
        "amort": float(prof.get('m_amort', 25.0)),
        "fixed_quote": float(prof.get('m_rate', 4.79)) if float(prof.get('m_rate', 0)) > 0 else float(intel['rates'].get('five_year_fixed_uninsured', 4.79)),
        "var_start": float(intel['rates'].get('five_year_variable', 5.50)),
        "target_rate": 3.00,
        "months_to_reach": 12,
        "initialized": True
    })

# --- 4. INLINE LOGO & TITLE ---
def get_inline_logo(img_name="logo.png", width=75):
    # Check root directory first, then fallback to looking one folder up
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
        
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Renewal Strategy: Fixed vs. Variable</h1>
    </div>
""", unsafe_allow_html=True)

# --- 5. STORYTELLING ---
name1_only = name1.split()[0]
name2_only = name2.split()[0] if name2 else "the market"

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-top: 0px; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; margin-bottom: 10px; font-size: 1.5em;">🔄 {household}: The Renewal Roulette</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{name1_only}</b> likes certainty. <b>{name2_only}</b> expects rates to drop. 
        This analysis pits <b>{name1_only}'s</b> need for a fixed path against <b>{name2_only}'s</b> forecast to see which strategy wins the math.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. CALCULATION ENGINE ---
def simulate_renewal_v3(balance, amort_rem, fixed_rate, var_start, target_rate, months_to_reach):
    months = 60 # 5-Year Term
    f_periodic = (fixed_rate / 100) / 12
    f_denom = ((1 + f_periodic)**(amort_rem*12) - 1)
    f_pmt = balance * (f_periodic * (1 + f_periodic)**(amort_rem*12)) / f_denom if f_denom != 0 else (balance / 12)
    
    total_change = target_rate - var_start
    monthly_step = total_change / months_to_reach if months_to_reach > 0 else 0
    
    v_balance, f_balance = balance, balance
    history, cum_v_int, cum_f_int = [], 0, 0
    
    for m in range(1, months + 1):
        curr_v_rate = var_start + (monthly_step * m) if m <= months_to_reach else target_rate
        v_periodic = (curr_v_rate / 100) / 12
        rem_months = (amort_rem * 12) - (m - 1)
        
        v_denom = ((1 + v_periodic)**rem_months - 1)
        v_pmt = v_balance * (v_periodic * (1 + v_periodic)**rem_months) / v_denom if v_denom != 0 else (v_balance / 12)
        
        v_int_mo = v_balance * v_periodic
        f_int_mo = f_balance * f_periodic
        cum_v_int += v_int_mo
        cum_f_int += f_int_mo
        
        v_balance -= (v_pmt - v_int_mo)
        f_balance -= (f_pmt - f_int_mo)
        
        history.append({
            "Month": m, "V_Rate": curr_v_rate, "F_Rate": fixed_rate,
            "V_Pmt": v_pmt, "F_Pmt": f_pmt, "Cum_V_Int": cum_v_int, "Cum_F_Int": cum_f_int
        })
    return history

# --- 7. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏦 Current Mortgage")
    balance = cloud_input("Remaining Mortgage Balance ($)", "renewal_analysis", "balance", step=1000.0) 
    amort = cloud_input("Remaining Am (Years)", "renewal_analysis", "amort", step=1.0) 
    fixed_quote = cloud_input("Fixed Rate Quote (%)", "renewal_analysis", "fixed_quote", step=0.01)

with col2:
    st.subheader("🎲 The Variable Forecast")
    var_start = cloud_input("Current Variable Rate (%)", "renewal_analysis", "var_start", step=0.01)
    target_rate = cloud_input("I expect the rate to reach (%)", "renewal_analysis", "target_rate", step=0.25)
    
    months_to_reach = st.slider("Months until it hits that target?", 1, 60, value=int(ren_store.get('months_to_reach', 12)), key="renewal_analysis:months_to_reach", on_change=sync_widget, args=("renewal_analysis:months_to_reach",))
    worst_case = st.toggle("🔥 Stress Test: 'Stay-High' Scenario", help="Simulates variable rates never dropping.")

final_target = var_start if worst_case else target_rate
history = simulate_renewal_v3(balance, amort, fixed_quote, var_start, final_target, months_to_reach)
df = pd.DataFrame(history)
df["Year"] = df["Month"] / 12 # Convert for plotting

# --- 8. METRICS ---
st.divider()
final = history[-1]
res1, res2 = st.columns(2)
res1.metric("Fixed Payment (Certainty)", f"${final['F_Pmt']:,.2f}")
res2.metric("Final Variable Payment (Forecast)", f"${final['V_Pmt']:,.2f}")

if final['Cum_V_Int'] < final['Cum_F_Int']:
    diff = final['Cum_F_Int'] - final['Cum_V_Int']
    st.success(f"🎯 **The Verdict: The Variable Path Wins.** Total interest savings: **${diff:,.0f}**.")
else:
    diff = final['Cum_V_Int'] - final['Cum_F_Int']
    st.error(f"🛡️ **The Verdict: The Fixed Path Wins.** The Variable path costs **${diff:,.0f}** MORE in interest.")

# --- 9. CHARTS (UPDATED TO YEARS) ---
st.markdown("### 📊 Deep Dive Analysis")
tab1, tab2, tab3 = st.tabs(["Rate Path", "Payment Change", "Cumulative Interest"])

with tab1:
    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df["Year"], y=df["V_Rate"], name="Variable Rate", line=dict(color=PRIMARY_GOLD, width=3), hovertemplate='Year %{x:.1f}: %{y:.2f}%'))
    fig_rate.add_trace(go.Scatter(x=df["Year"], y=df["F_Rate"], name="Fixed Rate", line=dict(color=CHARCOAL, dash='dash')))
    fig_rate.update_layout(plot_bgcolor="white", height=350, xaxis_title="Years", margin=dict(t=20, b=20))
    fig_rate.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_rate, use_container_width=True)

with tab2:
    fig_pmt = go.Figure()
    fig_pmt.add_trace(go.Scatter(x=df["Year"], y=df["V_Pmt"], name="Variable Payment", line=dict(color=PRIMARY_GOLD, width=3), hovertemplate='Year %{x:.1f}: $%{y:,.0f}'))
    fig_pmt.add_trace(go.Scatter(x=df["Year"], y=df["F_Pmt"], name="Fixed Payment", line=dict(color=CHARCOAL, dash='dash')))
    fig_pmt.update_layout(plot_bgcolor="white", height=350, xaxis_title="Years", margin=dict(t=20, b=20))
    fig_pmt.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_pmt, use_container_width=True)

with tab3:
    fig_int = go.Figure()
    fig_int.add_trace(go.Scatter(x=df["Year"], y=df["Cum_V_Int"], name="Total Var Interest", fill='tozeroy', line=dict(color=PRIMARY_GOLD), hovertemplate='Year %{x:.1f}: $%{y:,.0f}'))
    fig_int.add_trace(go.Scatter(x=df["Year"], y=df["Cum_F_Int"], name="Total Fixed Interest", line=dict(color=CHARCOAL, width=2)))
    fig_int.update_layout(plot_bgcolor="white", height=350, xaxis_title="Years", margin=dict(t=20, b=20))
    fig_int.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_int, use_container_width=True)

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
