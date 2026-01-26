import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import json

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL (DYNAMIC LINKING) ---
prof = st.session_state.get('user_profile', {})
name1 = prof.get('p1_name', 'Client')
name2 = prof.get('p2_name', '')
household = f"{name1} & {name2}" if name2 else name1

# Retrieve Market Intel for Variable Rate
def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_variable": 5.50, "five_year_fixed_uninsured": 4.79}}

intel = load_market_intel()

# --- 3. PERSISTENCE INITIALIZATION (REPAIRED MAPPING) ---
if "ren_store" not in st.session_state:
    # MAPPING REPAIR:
    # m_bal, m_amort, and m_rate are the keys defined in your streamlit_app.py
    initial_balance = float(prof.get('m_bal', 500000.0))
    initial_amort = float(prof.get('m_amort', 25.0))
    
    # Check if a rate exists in the profile; if 0.0 or None, use Market Intel
    profile_rate = prof.get('m_rate', 0.0)
    initial_fixed = float(profile_rate) if profile_rate > 0 else float(intel['rates'].get('five_year_fixed_uninsured', 4.79))

    st.session_state.ren_store = {
        "balance": initial_balance,
        "amort": initial_amort,
        "fixed_quote": initial_fixed,
        "var_start": float(intel['rates'].get('five_year_variable', 5.50)),
        "target_rate": 4.00,
        "months_to_reach": 24
    }

store = st.session_state.ren_store

# --- 4. PAGE HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=140)
with header_col2:
    st.title("Renewal Strategy: Fixed vs. Variable")

# --- 5. STORYTELLING SECTION (DYNAMIC NAMES) ---
# Mapping name1 to the "Fixed/Safe" seeker and name2 to the "Variable/Risk" taker
name1_only = name1.split()[0] # Use first name only for better flow
name2_only = name2.split()[0] if name2 else "the market"

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-top: 0px; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; margin-bottom: 10px; font-size: 1.5em;">🔄 {household}: The Renewal Roulette</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{name1_only}</b> likes to sleep at night knowing the mortgage payment is locked in stone. 
        However, <b>{name2_only}</b> believes the rates are on a downward trend and wants to capture the savings of a Variable path. 
        This analysis pits <b>{name1_only}'s</b> need for certainty against <b>{name2_only}'s</b> forecast to see which strategy wins the math.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. CALCULATION ENGINE ---
def simulate_renewal_v3(balance, amort_rem, fixed_rate, var_start, target_rate, months_to_reach):
    months = 60 # 5-Year Term
    f_periodic = (fixed_rate / 100) / 12
    f_pmt = balance * (f_periodic * (1 + f_periodic)**(amort_rem*12)) / ((1 + f_periodic)**(amort_rem*12) - 1)
    
    total_change = target_rate - var_start
    monthly_step = total_change / months_to_reach if months_to_reach > 0 else 0
    
    v_balance = balance
    f_balance = balance
    history = []
    cum_v_int = 0
    cum_f_int = 0
    
    for m in range(1, months + 1):
        curr_v_rate = var_start + (monthly_step * m) if m <= months_to_reach else target_rate
        v_periodic = (curr_v_rate / 100) / 12
        rem_months = (amort_rem * 12) - (m - 1)
        v_pmt = v_balance * (v_periodic * (1 + v_periodic)**rem_months) / ((1 + v_periodic)**rem_months - 1)
        
        v_int_mo = v_balance * v_periodic
        f_int_mo = f_balance * f_periodic
        cum_v_int += v_int_mo
        cum_f_int += f_int_mo
        
        v_balance -= (v_pmt - v_int_mo)
        f_balance -= (f_pmt - f_int_mo)
        
        history.append({
            "Month": m,
            "V_Rate": curr_v_rate,
            "F_Rate": fixed_rate,
            "V_Pmt": v_pmt,
            "F_Pmt": f_pmt,
            "Cum_V_Int": cum_v_int,
            "Cum_F_Int": cum_f_int
        })
    return history

# --- 7. INPUTS (LINKED TO STORE WITH TYPE CONSISTENCY) ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏦 Current Mortgage")
    # FIX: Ensure value and step are both floats
    balance = st.number_input("Remaining Balance ($)", value=float(store['balance']), step=1000.0, key="w_balance")
    store['balance'] = balance
    
    # FIX: Ensure value and step are both floats
    amort = st.number_input("Remaining Amortization (Years)", value=float(store['amort']), step=1.0, key="w_amort")
    store['amort'] = amort
    
    fixed_quote = st.number_input("Fixed Rate Quote (%)", value=float(store['fixed_quote']), step=0.01, key="w_fixed")
    store['fixed_quote'] = fixed_quote

with col2:
    st.subheader("🎲 The Variable Forecast")
    var_start = st.number_input("Current Variable Rate (%)", value=float(store['var_start']), step=0.01, key="w_var_start")
    store['var_start'] = var_start
    
    target_rate = st.number_input("I expect the rate to reach (%)", value=float(store['target_rate']), step=0.25, key="w_target")
    store['target_rate'] = target_rate
    
    months_to_reach = st.slider("Months until it hits that target?", 1, 60, value=int(store['months_to_reach']), key="w_months")
    store['months_to_reach'] = months_to_reach

# Execute
history = simulate_renewal_v3(balance, amort, fixed_quote, var_start, target_rate, months_to_reach)
df = pd.DataFrame(history)

# --- 8. METRICS & VERDICT ---
st.divider()
final = history[-1]
res1, res2 = st.columns(2)
res1.metric("Fixed Payment (Certainty)", f"${final['F_Pmt']:,.2f}")
res2.metric("Final Variable Payment (Forecast)", f"${final['V_Pmt']:,.2f}")

if final['Cum_V_Int'] < final['Cum_F_Int']:
    diff = final['Cum_F_Int'] - final['Cum_V_Int']
    st.success(f"""
        🎯 **The Verdict: The Variable Path Wins.** Based on this forecast, **{name2_only}** is correct. Choosing the Variable path is the better financial move because 
        it saves you **${diff:,.0f}** in total interest compared to the Fixed option over the 5-year term.
    """)
else:
    diff = final['Cum_V_Int'] - final['Cum_F_Int']
    st.error(f"""
        🛡️ **The Verdict: The Fixed Path Wins.** In this scenario, **{name1_only}** is correct. Even with the projected rate drops, the Variable path costs 
        **${diff:,.0f}** MORE in interest than the Fixed quote. The "Peace of Mind" option is actually the cheaper one here.
    """)

# --- 9. THE THREE CHARTS ---
st.markdown("### 📊 Deep Dive Analysis")
tab1, tab2, tab3 = st.tabs(["Rate Path", "Payment Change", "Cumulative Interest"])

with tab1:
    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=df["V_Rate"], name="Variable Rate", line=dict(color=PRIMARY_GOLD, width=3)))
    fig_rate.add_trace(go.Scatter(x=df["Month"], y=df["F_Rate"], name="Fixed Rate", line=dict(color=CHARCOAL, dash='dash')))
    fig_rate.update_layout(plot_bgcolor="white", height=350, yaxis=dict(ticksuffix="%"), margin=dict(t=20, b=20))
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

# --- 10. LEGAL ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong> This tool is for informational purposes only. Variable rate simulations are estimates. 
        Calculations assume monthly payment adjustments. Consult with a professional before renewing.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption("Analyst in a Pocket | Mortgage Renewal Hub")