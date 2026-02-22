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

# --- 6. THE RESULTS DASHBOARD (WITH RISK EVALUATION) ---
st.divider()
res1, res2, res3 = st.columns(3)

# Logic for Deal Grading
is_positive_cf = monthly_net > 0
is_infinite = cash_left <= 0

if is_infinite and is_positive_cf:
    status_headline = "💎 THE HOLY GRAIL"
    status_color = "#5cb85c" # Green
    status_text = "Infinite return with positive cash flow. This deal is a massive accelerator for your portfolio."
elif is_positive_cf:
    status_headline = "✅ SOLID RENTAL"
    status_color = "#CEB36F" # Gold
    status_text = f"You have ${cash_left:,.0f} tied up, but the property pays for itself and more."
elif monthly_net < 0:
    status_headline = "🚨 CASH FLOW WARNING"
    status_color = "#d9534f" # Red
    status_text = "<b>DANGER:</b> This property is 'underwater' monthly. This will likely hurt your ability to borrow for the next deal."

# Metric Row
if is_infinite:
    res1.metric("Cash Left in Deal", "$0", delta="Infinite!", delta_color="normal")
    coc_display = "∞"
else:
    res1.metric("Cash Left in Deal", f"${cash_left:,.0f}", delta="Stuck", delta_color="inverse")
    coc_return = (monthly_net * 12) / cash_left * 100
    coc_display = f"{coc_return:.1f}%"

res2.metric("Equity Created", f"${round(arv - new_loan_amount, -3):,.0f}")
res3.metric("Est. Net Cash Flow", f"${monthly_net:,.0f}/mo", delta="Negative" if not is_positive_cf else "Positive", delta_color="normal" if is_positive_cf else "inverse")

# The Verdict Box
st.markdown(f"""
<div style="text-align: center; margin-top: 20px; padding: 15px 25px; border-radius: 10px; border: 2px solid {status_color}; background-color: {status_color}10;">
    <h3 style="color: {status_color}; margin: 0; font-size: 1.4em; font-weight: 700;">{status_headline}</h3>
    <p style="color: {SLATE_ACCENT}; margin: 8px 0 0 0; font-size: 1.1em;">{status_text}</p>
</div>
""", unsafe_allow_html=True)

# --- 7. STRATEGIC INSIGHTS (REFINED UI) ---
st.write("")
st.subheader("📋 Deal Analysis & Recommendations")

# Define a softer "Warning" color (a sophisticated Amber/Orange)
WARNING_AMBER = "#D97706" 

if monthly_net < 0:
    # We use a standard container or a custom div instead of st.error
    st.markdown(f"""
    <div style="background-color: {WARNING_AMBER}15; padding: 20px; border-radius: 10px; border: 1px solid {WARNING_AMBER};">
        <h4 style="color: {WARNING_AMBER}; margin-top: 0;">⚠️ Cash Flow Sensitivity</h4>
        <p style="color: {SLATE_ACCENT};">This deal is currently showing a monthly deficit of <b>${abs(monthly_net):,.0f}</b>. Here is why this matters for your portfolio growth:</p>
        
        <ul style="color: {SLATE_ACCENT}; line-height: 1.6;">
            <li><b>Borrowing Power:</b> Lenders look for a <b>DSCR (Debt Service Coverage Ratio)</b> of ~1.2x. A negative cash flow reduces your "Global Cash Flow" and can stop you from getting your next loan.</li>
            <li><b>The "Repeat" Step:</b> Funding this loss from your personal income slows down your ability to save for the next acquisition.</li>
        </ul>
        
        <hr style="border: 0; border-top: 1px solid {WARNING_AMBER}50; margin: 15px 0;">
        
        <h4 style="color: {WARNING_AMBER};">Ways to Optimize this Deal:</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px;">
            <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                <span style="font-size: 1.2em;">📉</span><br><b>Adjust LTV</b><br><span style="font-size: 0.85em;">Try a {refi_ltv*100 - 5:.0f}% Refi to lower the payment.</span>
            </div>
            <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                <span style="font-size: 1.2em;">🛠️</span><br><b>Lower OpEx</b><br><span style="font-size: 0.85em;">Self-manage or shop insurance for better rates.</span>
            </div>
            <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid {WARNING_AMBER}30; text-align: center;">
                <span style="font-size: 1.2em;">💰</span><br><b>Value-Add</b><br><span style="font-size: 0.85em;">Improve the unit to command a higher market rent.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif is_infinite:
    st.success("✨ **The Perfect BRRRR:** You've recovered your initial capital. Focus on maintaining high occupancy while looking for your next property.")
else:
    st.info(f"📈 **Wealth Builder:** This property is self-sustaining and earning a **{coc_display}** Cash-on-Cash return.")

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
