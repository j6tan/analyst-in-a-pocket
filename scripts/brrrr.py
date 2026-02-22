import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import os
import base64
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, load_user_data, init_session_state

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile', {}).get('p1_name'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
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

# Personalized Greeting
prof = st.session_state.app_db.get('profile', {})
p1_raw = prof.get('p1_name', '').strip() if isinstance(prof.get('p1_name'), str) else ''
p2_raw = prof.get('p2_name', '').strip() if isinstance(prof.get('p2_name'), str) else ''
greeting_names = f"{p1_raw} & {p2_raw}" if p1_raw and p2_raw else (p1_raw or "Investor")

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>The BRRRR Engine</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🔓 Recycled Wealth</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Listen up, <b>{greeting_names}</b>. Real estate is the only asset class that lets you buy your cake, eat it, and then get your money back to buy another. This model analyzes how much of your capital you can "pull back out" of a deal to keep your velocity of money high.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. INPUTS: THE DEAL ---
st.header("🛠️ Phase 1: Buy & Rehab")
c1, c2 = st.columns(2)

with c1:
    buy_price = st.number_input("Purchase Price ($)", value=125000, step=5000)
    rehab_budget = st.number_input("Rehab Costs ($)", value=40000, step=1000)
    
with c2:
    arv = st.number_input("After Repair Value (ARV) ($)", value=225000, step=5000)
    buying_holding = st.number_input("Closing & Holding Costs ($)", value=5000, step=500)

total_invested = buy_price + rehab_budget + buying_holding

st.header("🏦 Phase 2: Rent & Refi")
c3, c4 = st.columns(2)

with c3:
    monthly_rent = st.number_input("Expected Monthly Rent ($)", value=1850, step=50)
    refi_ltv = st.slider("Refinance LTV (%)", 60, 80, 75) / 100

with c4:
    refi_rate = st.number_input("New Mortgage Rate (%)", value=6.75, step=0.1)
    refi_closing = st.number_input("Refi Closing Costs ($)", value=4000, step=500)

# --- 5. MATH ENGINE (ROUNDED TO 1,000) ---
new_loan_amount = round(arv * refi_ltv, -3)
net_proceeds = round(new_loan_amount - refi_closing, -3)
cash_left = round(total_invested - net_proceeds, -3)

# Monthly Cash Flow Math
monthly_piti = (new_loan_amount * (refi_rate/100/12)) / (1 - (1 + refi_rate/100/12)**-360)
opex_buffer = monthly_rent * 0.25 # 25% for taxes, insurance, repairs
monthly_net = round(monthly_rent - monthly_piti - opex_buffer, 0)

# --- 6. THE RESULTS DASHBOARD (BALANCED VERSION) ---
st.divider()

# First Row: The Big Three
res1, res2, res3 = st.columns(3)

# Cash Left Calculation
if cash_left <= 0:
    res1.metric("Cash Left in Deal", "$0", delta="Infinite Return!", delta_color="normal")
    status_headline = "🔥 THE PERFECT BRRRR"
    status_color = "#5cb85c"
    status_text = f"Capital fully recycled. You own this property for <b>$0</b> net investment."
    coc_display = "∞ (Infinite)"
else:
    res1.metric("Cash Left in Deal", f"${cash_left:,.0f}", delta="Capital Stuck", delta_color="inverse")
    status_headline = "🧱 CAPITAL COMMITTED"
    status_color = "#2B5C8F"
    status_text = f"<b>${cash_left:,.0f}</b> of your capital remains tied up in this asset."
    # Cash on Cash Return calculation
    coc_return = (monthly_net * 12) / cash_left * 100
    coc_display = f"{coc_return:.1f}%"

res2.metric("Equity Created", f"${round(arv - new_loan_amount, -3):,.0f}")
res3.metric("Est. Net Cash Flow", f"${monthly_net:,.0f}/mo")

# The Verdict Box
st.markdown(f"""
<div style="text-align: center; margin-top: 20px; padding: 15px 25px; border-radius: 10px; border: 2px solid {status_color}; background-color: {status_color}10;">
    <h3 style="color: {status_color}; margin: 0; font-size: 1.4em; font-weight: 700; letter-spacing: 0.5px;">{status_headline}</h3>
    <p style="color: {SLATE_ACCENT}; margin: 8px 0 0 0; font-size: 1.1em; line-height: 1.4;">{status_text}</p>
</div>
""", unsafe_allow_html=True)

# --- 7. SECONDARY PERFORMANCE METRICS (Replacing the Chart) ---
st.write("")
st.subheader("📊 Performance Deep Dive")
m1, m2, m3 = st.columns(3)

# 1. Cash on Cash Return (Annual Cash Flow / Cash Left)
m1.metric("Cash on Cash Return", coc_display, help="Annual Cash Flow divided by the cash you have left in the deal.")

# 2. Loan to Value (Actual)
actual_ltv = (new_loan_amount / arv) * 100
m2.metric("Post-Refi LTV", f"{actual_ltv:.1f}%", help="Your actual debt-to-value ratio after the bank's appraisal.")

# 3. Forced Appreciation
forced_app = arv - buy_price - rehab_budget
m3.metric("Forced Appreciation", f"${round(forced_app, -3):,.0f}", help="The 'sweat equity' value created through your renovation.")

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
