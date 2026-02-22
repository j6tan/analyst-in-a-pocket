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

# Personalized Greeting based on profile data
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
        Listen up, <b>{greeting_names}</b>. Real estate lets you buy your cake, eat it, and then get your money back to buy another. This model analyzes your capital recycling velocity.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. INPUTS: THE DEAL (Synced to Cloud) ---
st.header("🛠️ Phase 1: Buy & Rehab")
c1, c2 = st.columns(2)

with c1:
    buy_price = cloud_input("Purchase Price ($)", "brrrr_buy_price", 125000)
    rehab_budget = cloud_input("Rehab Costs ($)", "brrrr_rehab_budget", 40000)
    
with c2:
    arv = cloud_input("After Repair Value (ARV) ($)", "brrrr_arv", 225000)
    buying_holding = cloud_input("Closing & Holding Costs ($)", "brrrr_holding", 5000)

total_invested = buy_price + rehab_budget + buying_holding

st.header("🏦 Phase 2: Rent & Refi")
c3, c4 = st.columns(2)

with c3:
    monthly_rent = cloud_input("Expected Monthly Rent ($)", "brrrr_rent", 1850)
    refi_ltv_val = st.slider("Refinance LTV (%)", 60, 80, 75)
    refi_ltv = refi_ltv_val / 100

with c4:
    refi_rate = cloud_input("New Mortgage Rate (%)", "brrrr_refi_rate", 4.0)
    refi_closing = cloud_input("Refi Closing Costs ($)", "brrrr_refi_costs", 4000)

# --- 5. MATH ENGINE (CRASH-PROOF) ---
new_loan_amount = round(arv * refi_ltv, -3)
net_proceeds = round(new_loan_amount - refi_closing, -3)
cash_left = round(total_invested - net_proceeds, -3)

# Safety check for 0% interest rate to avoid ZeroDivisionError
r_monthly = (refi_rate / 100) / 12
n_months = 360

if r_monthly > 0:
    monthly_piti = (new_loan_amount * r_monthly) / (1 - (1 + r_monthly)**-n_months)
else:
    # If interest is 0, it's just Principal / Months
    monthly_piti = new_loan_amount / n_months if n_months > 0 else 0

opex_buffer = monthly_rent * 0.25 
monthly_net = round(monthly_rent - monthly_piti - opex_buffer, 0)

# Safety check for DSCR (cannot divide by 0 mortgage payment)
noi_annual = (monthly_rent - opex_buffer) * 12
debt_annual = monthly_piti * 12

if debt_annual > 0:
    dscr = noi_annual / debt_annual
else:
    # If no debt, DSCR is technically infinite, but we'll set a high floor for the UI
    dscr = 99.0 if noi_annual > 0 else 0.0

# --- 6. THE RESULTS DASHBOARD ---
st.divider()
res1, res2, res3 = st.columns(3)

is_positive_cf = monthly_net > 0
is_infinite = cash_left <= 0

if is_infinite and is_positive_cf:
    status_headline, status_color = "💎 THE HOLY GRAIL", "#5cb85c"
    status_text = "Infinite return with positive cash flow. Portfolio accelerator."
elif is_positive_cf:
    status_headline, status_color = "✅ SOLID RENTAL", "#CEB36F"
    status_text = f"You have ${cash_left:,.0f} tied up, but the property pays for itself."
else:
    status_headline, status_color = "⚠️ CASH FLOW WARNING", "#D97706"
    status_text = f"This property is showing a monthly deficit of <b>${abs(monthly_net):,.0f}</b>."

# Metrics Row
if is_infinite:
    res1.metric("Cash Left in Deal", "$0", delta="Infinite Return!", delta_color="normal")
    coc_display = "∞"
else:
    res1.metric("Cash Left in Deal", f"${cash_left:,.0f}", delta="Capital Stuck", delta_color="inverse")
    coc_display = f"{((monthly_net * 12) / cash_left * 100):.1f}%"

res2.metric("Equity Created", f"${round(arv - new_loan_amount, -3):,.0f}")
res3.metric("Est. Net Cash Flow", f"${monthly_net:,.0f}/mo")

# The Verdict Box
st.markdown(f"""
<div style="text-align: center; margin-top: 20px; padding: 15px 25px; border-radius: 10px; border: 2px solid {status_color}; background-color: {status_color}10;">
    <h3 style="color: {status_color}; margin: 0; font-size: 1.4em; font-weight: 700;">{status_headline}</h3>
    <p style="color: {SLATE_ACCENT}; margin: 8px 0 0 0; font-size: 1.1em;">{status_text}</p>
</div>
""", unsafe_allow_html=True)

# --- 7. STRATEGIC INSIGHTS ---
st.write("")
st.subheader("📋 Deal Analysis & Recommendations")

if monthly_net < 0:
    html_rec = f"""
<div style="background-color: #D9770615; padding: 20px; border-radius: 10px; border: 1px solid #D97706;">
    <h4 style="color: #D97706; margin-top: 0;">⚠️ Cash Flow Sensitivity</h4>
    <p style="color: {SLATE_ACCENT};">Why this matters for your portfolio growth:</p>
    <ul style="color: {SLATE_ACCENT}; line-height: 1.6;">
        <li><b>Borrowing Power:</b> Your <b>DSCR is {dscr:.2f}</b>. Lenders typically want 1.20+. This could stop your next loan.</li>
        <li><b>Velocity:</b> Personal income used to fund losses cannot be used for the next down payment.</li>
    </ul>
    <hr style="border: 0; border-top: 1px solid #D9770650; margin: 15px 0;">
    <h4 style="color: #D97706;">Optimization Toolkit:</h4>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px;">
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid #D9770630; text-align: center;">
            <span style="font-size: 1.2em;">📉</span><br><b style="color: {CHARCOAL};">Adjust LTV</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Try {refi_ltv_val - 5}% LTV.</span>
        </div>
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid #D9770630; text-align: center;">
            <span style="font-size: 1.2em;">🛠️</span><br><b style="color: {CHARCOAL};">Lower OpEx</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Self-manage or shop insurance.</span>
        </div>
        <div style="background: white; padding: 10px; border-radius: 5px; border: 1px solid #D9770630; text-align: center;">
            <span style="font-size: 1.2em;">💰</span><br><b style="color: {CHARCOAL};">Value-Add</b><br><span style="font-size: 0.85em; color: {SLATE_ACCENT};">Increase the market rent.</span>
        </div>
    </div>
</div>
"""
    st.markdown(html_rec, unsafe_allow_html=True)
elif is_infinite:
    st.success("✨ **The Perfect BRRRR:** You've recovered your capital. Focus on high occupancy and Deal #2.")
else:
    st.info(f"📈 **Wealth Builder:** Property is earning a **{coc_display}** Cash-on-Cash return.")

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
