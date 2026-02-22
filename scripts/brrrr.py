import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from style_utils import inject_global_css, show_disclaimer
from data_handler import init_session_state

init_session_state()
inject_global_css()

if st.button("⬅️ Back to Home"):
    st.switch_page("home.py")

st.title("🏘️ BRRRR Strategy Deal Analyzer")
st.markdown("""
Use this model to analyze a "Buy, Rehab, Rent, Refinance, Repeat" deal. 
The goal is to maximize your **Equity** while minimizing the **Cash** you leave stuck in the property.
""")

# --- 1. INPUTS: THE BUY & REHAB ---
st.header("1. Acquisition & Renovation")
col1, col2 = st.columns(2)

with col1:
    buy_price = st.number_input("Purchase Price ($)", value=120000, step=5000)
    closing_costs_buy = st.number_input("Purchase Closing Costs ($)", value=3000, step=500)
    rehab_budget = st.number_input("Rehab Budget ($)", value=35000, step=1000)

with col2:
    arv = st.number_input("After Repair Value (ARV) ($)", value=210000, step=5000)
    holding_costs = st.number_input("Holding Costs (Interest/Utilities during rehab) ($)", value=2000, step=500)

total_project_cost = buy_price + closing_costs_buy + rehab_budget + holding_costs

# --- 2. INPUTS: THE REFINANCE ---
st.header("2. The Refinance (The Exit)")
c1, c2 = st.columns(2)

with c1:
    refi_ltv = st.slider("Refinance Loan-to-Value (LTV) %", 60, 80, 75) / 100
    refi_rate = st.number_input("New Mortgage Interest Rate (%)", value=6.5, step=0.1)

with c2:
    closing_costs_refi = st.number_input("Refi Closing Costs ($)", value=4000, step=500)
    monthly_rent = st.number_input("Expected Monthly Rent ($)", value=1800, step=50)

# --- 3. THE MATH ENGINE ---
new_loan_amount = arv * refi_ltv
net_refi_proceeds = new_loan_amount - closing_costs_refi
cash_left_in_deal = total_project_cost - net_refi_proceeds

# Monthly Expenses (Simplified)
monthly_piti = (new_loan_amount * (refi_rate/100/12)) / (1 - (1 + refi_rate/100/12)**-360)
other_expenses = monthly_rent * 0.25 # 25% for Taxes, Insurance, Maint, CapEx
monthly_cash_flow = monthly_rent - monthly_piti - other_expenses

# --- 4. THE DASHBOARD ---
st.divider()
res1, res2, res3 = st.columns(3)

# Metric 1: Cash Position
if cash_left_in_deal <= 0:
    res1.metric("Cash Left in Deal", "$0", delta="Infinite Return!", delta_color="normal")
else:
    res1.metric("Cash Left in Deal", f"${cash_left_in_deal:,.0f}", delta="Capital Stuck", delta_color="inverse")

# Metric 2: Equity Created
equity = arv - new_loan_amount
res2.metric("Equity Created", f"${equity:,.0f}", f"{((equity/arv)*100):.1f}% Equity")

# Metric 3: Cash Flow
res3.metric("Est. Monthly Cash Flow", f"${monthly_cash_flow:,.0f}", "After 25% OpEx")

# --- 5. VISUALIZING THE CAPITAL RECYCLING ---
st.subheader("📊 Capital Breakdown")

labels = ['Purchase', 'Rehab/Hold', 'Closing Costs']
values = [buy_price, rehab_budget + holding_costs, closing_costs_buy + closing_costs_refi]

fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3, marker_colors=['#2E2B28', '#CEB36F', '#4A4E5A'])])
fig.update_layout(title_text="Where your money goes (Pre-Refi)")
st.plotly_chart(fig, use_container_width=True)

# THE REALITY CHECK
if cash_left_in_deal > (total_project_cost * 0.20):
    st.warning(f"⚠️ **Warning:** You are leaving **${cash_left_in_deal:,.0f}** in this deal. This is more than a standard 20% down payment. It might be better to just buy a turnkey property unless you expect high appreciation.")
elif cash_left_in_deal <= 0:
    st.success(f"🔥 **The Perfect BRRRR:** You effectively own this property for $0 of your own money. You are ready to REPEAT immediately.")
else:
    st.info(f"✅ **Good Deal:** You have recycled most of your capital. You only have ${cash_left_in_deal:,.0f} tied up in a ${arv:,.0f} asset.")

show_disclaimer()

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; color: #adb5bd; font-size: 0.85em; margin-top: 50px; padding-top: 20px; border-top: 1px solid #dee2e6;">
        &copy; 2026 FIRE Calculator. All rights reserved. <br>
        <span style="font-size: 0.9em; font-style: italic;">Empowering Canadian professionals to build wealth.</span>
    </div>
""", unsafe_allow_html=True)
