import streamlit as st
import pandas as pd
import time
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.get('data_loaded'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        st.session_state.data_loaded = True
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME VARIABLES ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
WARNING_AMBER = "#D97706"

# --- 3. LOGO & STORYTELLING ---
def get_inline_logo(img_name="logo.png", width=75):
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🏘️</span>"

logo_html = get_inline_logo(width=75)
prof = st.session_state.app_db.get('profile', {})
greeting = prof.get('p1_name', 'Investor')

st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0;'>The BRRRR Engine</h1>
    </div>
""", unsafe_allow_html=True)

# --- 4. INPUTS: THE DEAL (DEFINED BEFORE MATH) ---
st.header("🛠️ Phase 1: Buy & Rehab")
c1, c2 = st.columns(2)
with c1:
    buy_price = cloud_input("Purchase Price ($)", "brrrr_buy_price", 125000)
    rehab_budget = cloud_input("Rehab Costs ($)", "brrrr_rehab_budget", 40000)
with c2:
    arv = cloud_input("After Repair Value (ARV) ($)", "brrrr_arv", 225000)
    holding = cloud_input("Holding/Closing ($)", "brrrr_holding", 5000)

total_invested = buy_price + rehab_budget + holding

st.header("🏦 Phase 2: Rent & Refi")
c3, c4 = st.columns(2)
with c3:
    monthly_rent = cloud_input("Monthly Rent ($)", "brrrr_rent", 1850)
    refi_ltv_pct = st.slider("Refinance LTV (%)", 50, 85, 75, key="brrrr_ltv_slider")
    refi_ltv = refi_ltv_pct / 100
with c4:
    refi_rate = cloud_input("Refi Interest Rate (%)", "brrrr_refi_rate", 4.0)
    refi_costs = cloud_input("Refi Closing Costs ($)", "brrrr_refi_costs", 4000)

# --- 5. MATH ENGINE (CRASH-PROOF) ---
new_loan = round(arv * refi_ltv, -3)
net_proceeds = round(new_loan - refi_costs, -3)
cash_left = round(total_invested - net_proceeds, -3)

# PITI Calculation
r_monthly = (refi_rate / 100) / 12
if r_monthly > 0:
    monthly_piti = (new_loan * r_monthly) / (1 - (1 + r_monthly)**-360)
else:
    monthly_piti = new_loan / 360

opex = monthly_rent * 0.25 
monthly_net = round(monthly_rent - monthly_piti - opex, 0)

# DSCR Calculation
noi_annual = (monthly_rent - opex) * 12
debt_annual = monthly_piti * 12
dscr = noi_annual / debt_annual if debt_annual > 0 else 99.0

# --- 6. RESULTS DASHBOARD ---
st.divider()
res1, res2, res3 = st.columns(3)

is_positive = monthly_net > 0
is_infinite = cash_left <= 0

if is_infinite and is_positive:
    status_h, status_c = "💎 THE HOLY GRAIL", "#5cb85c"
    status_t = "Infinite return + positive cash flow. This is perfect velocity."
elif is_positive:
    status_h, status_c = "✅ SOLID RENTAL", PRIMARY_GOLD
    status_t = f"You have ${max(0, cash_left):,.0f} tied up, but it's a performing asset."
else:
    status_h, status_c = "⚠️ CASH FLOW WARNING", WARNING_AMBER
    status_t = f"This property is costing you <b>${abs(monthly_net):,.0f}</b> per month."

res1.metric("Cash Left in Deal", f"${max(0, cash_left):,.0f}", delta="Infinite Return" if is_infinite else None)
res2.metric("Equity Created", f"${round(arv - new_loan, -3):,.0f}")
res3.metric("Monthly Net", f"${monthly_net:,.0f}", delta="Negative" if not is_positive else "Positive", delta_color="normal" if is_positive else "inverse")

st.markdown(f"""
<div style="text-align: center; margin-top: 20px; padding: 15px 25px; border-radius: 10px; border: 2px solid {status_c}; background-color: {status_c}10;">
    <h3 style="color: {status_c}; margin: 0; font-size: 1.4em; font-weight: 700;">{status_h}</h3>
    <p style="color: {SLATE_ACCENT}; margin: 8px 0 0 0; font-size: 1.1em;">{status_t}</p>
</div>
""", unsafe_allow_html=True)

# --- 7. STRATEGIC INSIGHTS ---
if monthly_net < 0:
    html_rec = f"""
<div style="background-color: {WARNING_AMBER}15; padding: 20px; border-radius: 10px; border: 1px solid {WARNING_AMBER}; margin-top: 25px;">
    <h4 style="color: {WARNING_AMBER}; margin-top: 0;">📋 Risk Analysis</h4>
    <p style="color: {SLATE_ACCENT};">Current DSCR: <b>{dscr:.2f}</b>. Lenders typically look for 1.20+. Negative cash flow can slow your ability to repeat the process.</p>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; margin-top: 15px;">
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30;">
            <b>Lower LTV</b><br><span style="font-size: 0.85em;">Try {refi_ltv_pct - 10}%</span>
        </div>
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30;">
            <b>Cut OpEx</b><br><span style="font-size: 0.85em;">Self-manage</span>
        </div>
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30;">
            <b>Rent Hike</b><br><span style="font-size: 0.85em;">Value-add</span>
        </div>
    </div>
</div>
"""
    st.markdown(html_rec, unsafe_allow_html=True)

show_disclaimer()
