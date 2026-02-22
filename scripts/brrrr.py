import streamlit as st
import pandas as pd
import time
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()

# Crucial Fix: Prevent the "revert to default" by ensuring data is loaded once
if st.session_state.get('username') and not st.session_state.get('brrrr_initialized'):
    with st.spinner("🔄 syncing your deal data..."):
        load_user_data(st.session_state.username)
        st.session_state['brrrr_initialized'] = True
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
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px;">'
    return "🏘️"

st.markdown(f"<div style='display: flex; align-items: center; gap: 15px;'>{get_inline_logo()} <h1 style='margin:0;'>The BRRRR Engine</h1></div>", unsafe_allow_html=True)

# --- 4. INPUTS: THE DEAL ---
st.header("🛠️ Phase 1: Buy & Rehab")
c1, c2 = st.columns(2)

with c1:
    # Use unique keys so Streamlit preserves state during reruns
    buy_price = cloud_input("Purchase Price ($)", "brrrr_buy_price", 0)
    rehab_budget = cloud_input("Rehab Costs ($)", "brrrr_rehab_budget", 0)
    
with c2:
    arv = cloud_input("After Repair Value (ARV) ($)", "brrrr_arv", 0)
    holding = cloud_input("Holding & Closing ($)", "brrrr_holding", 0)

total_invested = buy_price + rehab_budget + holding

st.header("🏦 Phase 2: Rent & Refi")
c3, c4 = st.columns(2)

with c3:
    monthly_rent = cloud_input("Monthly Rent ($)", "brrrr_rent", 0)
    # The slider needs a unique key to prevent resetting
    refi_ltv_pct = st.slider("Refinance LTV (%)", 50, 85, 75, key="brrrr_ltv_slider")
    refi_ltv = refi_ltv_pct / 100

with c4:
    refi_rate = cloud_input("Refi Interest Rate (%)", "brrrr_refi_rate", 4.0)
    refi_costs = cloud_input("Refi Closing Costs ($)", "brrrr_refi_costs", 4000)

# --- 5. MATH ENGINE ---
# Ensure math only runs if we have values to avoid errors
if arv > 0 and refi_rate > 0:
    new_loan = round(arv * refi_ltv, -3)
    net_proceeds = round(new_loan - refi_costs, -3)
    cash_left = round(total_invested - net_proceeds, -3)

    r_monthly = (refi_rate / 100) / 12
    monthly_piti = (new_loan * r_monthly) / (1 - (1 + r_monthly)**-360)
    
    opex = monthly_rent * 0.25 
    monthly_net = round(monthly_rent - monthly_piti - opex, 0)
    
    noi_annual = (monthly_rent - opex) * 12
    debt_annual = monthly_piti * 12
    dscr = noi_annual / debt_annual if debt_annual > 0 else 0

    # --- 6. RESULTS ---
    st.divider()
    res1, res2, res3 = st.columns(3)
    
    is_positive = monthly_net > 0
    is_infinite = cash_left <= 0

    res1.metric("Cash Left in Deal", f"${max(0, cash_left):,.0f}", delta="Infinite Return" if is_infinite else None)
    res2.metric("Equity Created", f"${round(arv - new_loan, -3):,.0f}")
    res3.metric("Monthly Net", f"${monthly_net:,.0f}", delta="Negative" if not is_positive else "Positive", delta_color="normal" if is_positive else "inverse")

    # --- 7. RECOMMENDATIONS (FIXED HTML) ---
    if not is_positive:
        st.markdown(f"""
        <div style="background-color: {WARNING_AMBER}15; padding: 20px; border-radius: 10px; border: 1px solid {WARNING_AMBER}; margin-top: 20px;">
            <h4 style="color: {WARNING_AMBER}; margin-top: 0;">📋 Deal Analysis</h4>
            <p style="color: {SLATE_ACCENT};"><b>DSCR: {dscr:.2f}</b>. Lenders usually want 1.20+. This property will likely hurt your ability to borrow for your next house.</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <b>Lower LTV</b><br><span style="font-size: 0.8em;">Try {refi_ltv_pct-10}%</span>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <b>Cut OpEx</b><br><span style="font-size: 0.8em;">Self-manage</span>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                    <b>Value Add</b><br><span style="font-size: 0.8em;">Increase Rent</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Enter your Purchase Price and ARV to see the analysis.")

show_disclaimer()
