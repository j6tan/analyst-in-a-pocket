import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. CALCULATION ENGINE ---
def run_wealth_engine(price, inv, rate, apprec, r_income, costs, alt_return, years, tax_rate):
    # Mortgage Logic
    loan = price - inv
    m_rate = (rate/100)/12
    n_months = 25 * 12
    monthly_pi = loan * (m_rate * (1+m_rate)**n_months) / ((1+m_rate)**n_months - 1)
    
    # Setup
    curr_val, curr_loan, curr_rent = price, loan, r_income
    stock_portfolio = inv + (price * 0.02) # DP + ~2% Buying Costs (Legal/LTT)
    stock_contributions = stock_portfolio
    
    data = []
    for y in range(1, years + 1):
        # Debt Paydown
        for _ in range(12):
            curr_loan -= (monthly_pi - (curr_loan * m_rate))
        
        # Growth
        curr_val *= (1 + apprec/100)
        stock_portfolio *= (1 + alt_return/100)
        
        data.append({
            "Year": y,
            "RE_Equity": max(0, curr_val - curr_loan),
            "Stock_Value": stock_portfolio
        })

    # --- FINAL EXIT CALCULATIONS ---
    # 1. Rental Exit (3% Comm + $1500 Legal)
    re_selling_costs = (curr_val * 0.03) + 1500
    re_profit = curr_val - price - re_selling_costs
    re_tax = max(0, re_profit * 0.50 * (tax_rate/100)) # 50% Inclusion Rate
    final_re_wealth = (curr_val - curr_loan - re_selling_costs) - re_tax
    
    # 2. Stock Exit
    stock_profit = stock_portfolio - stock_contributions
    stock_tax = max(0, stock_profit * 0.50 * (tax_rate/100)) # 50% Inclusion Rate
    final_stock_wealth = stock_portfolio - stock_tax
    
    return pd.DataFrame(data), final_re_wealth, final_stock_wealth, re_tax, stock_tax, re_selling_costs

# --- 3. PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Investment Wealth Analyst")

# --- STANDARDIZED HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2: st.title("Rental Property vs. Stock Portfolio")

# --- 4. STORYTELLING: SARAH & JAMES ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; margin-bottom: 10px; font-size: 1.5em;">💼 Sarah & James’s $200,000 Crossroads</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        After a great year, <b>Sarah and James</b> have a <b>$200,000 nest egg</b> ready to deploy. They are debating two very different paths to retirement: Sarah's leveraged rental property or James's passive stock portfolio. Which path gets them to their goal faster?
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Real Estate Asset")
    price = st.number_input("Purchase Price ($)", value=800000, step=25000)
    inv = st.number_input("Down Payment ($)", value=200000, step=5000)
    rate = st.number_input("Mortgage Rate (%)", value=4.5, step=0.1)
    rent = st.number_input("Monthly Rent ($)", value=3200)
    apprec = st.slider("Annual Appreciation (%)", 0.0, 7.0, 3.0)
    
    with st.expander("🛠️ Property Operating Costs"):
        tax = st.number_input("Annual Property Tax ($)", value=3200)
        ins = st.number_input("Monthly Insurance ($)", value=125)
        strata = st.number_input("Monthly Strata ($)", value=450)
        rm = st.number_input("Annual Maintenance ($)", value=2000)
        mgmt = st.slider("Mgmt Fee (%)", 0, 10, 0)

with col2:
    st.subheader("📈 Stock Portfolio")
    alt_ret = st.number_input("Portfolio Growth (%)", value=7.0, step=0.5)
    years = st.select_slider("Holding Period (Years)", options=[5, 10, 15, 20, 25], value=10)
    st.subheader("⚖️ Tax & Exit")
    m_tax_rate = st.number_input("Your Marginal Tax Rate (%)", value=35, help="The rate you pay on your highest dollar of income.")

# Execution
df, re_wealth, stock_wealth, re_tax, stock_tax, re_costs = run_wealth_engine(
    price, inv, rate, apprec, rent, 
    {'tax': tax, 'ins': ins, 'strata': strata, 'rm': rm, 'mgmt': mgmt},
    alt_ret, years, m_tax_rate
)

# --- 6. VISUALS ---
st.divider()
st.subheader("📊 Final Wealth (After Tax & Debt)")

# Comparison Bar Chart
fig_wealth = go.Figure(data=[
    go.Bar(name='Rental (Net)', x=['Rental Path'], y=[re_wealth], marker_color=PRIMARY_GOLD, text=[f"${re_wealth:,.0f}"], textposition='auto'),
    go.Bar(name='Stocks (Net)', x=['Stock Path'], y=[stock_wealth], marker_color=CHARCOAL, text=[f"${stock_wealth:,.0f}"], textposition='auto')
])
fig_wealth.update_layout(yaxis=dict(tickformat="$,.0f"), height=450)
st.plotly_chart(fig_wealth, use_container_width=True)

# --- 7. EXIT SUMMARY BOX ---
st.markdown(f"""
<div style="background-color: #FFF9E6; padding: 20px; border-radius: 8px; border: 1px solid #FFE58F; margin-top: 25px; margin-bottom: 25px;">
    <h4 style="margin-top: 0; color: #856404;">⚠️ Exit Strategy Math (Year {years})</h4>
    <p>When you liquidate in Year {years}, here is the breakdown of the "leakage":</p>
    <ul>
        <li><b>Rental Path:</b> Deducted <b>${re_costs:,.0f}</b> for closing (3% + $1500) and <b>${re_tax:,.0f}</b> in Capital Gains Tax.</li>
        <li><b>Stock Path:</b> Deducted <b>${stock_tax:,.0f}</b> in Capital Gains Tax on portfolio growth.</li>
        <li><b>Note:</b> Tax assumes a 50% inclusion rate in your {m_tax_rate}% marginal bracket.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# --- 8. STRATEGIC ANALYST INSIGHT ---
st.subheader("🎯 Strategic Analyst Insight")
insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    diff = abs(re_wealth - stock_wealth)
    winner = "Rental Property" if re_wealth > stock_wealth else "Stock Portfolio"
    st.success(f"**The Verdict:** The **{winner}** is the superior path by **${diff:,.0f}**.")
    st.write(f"This accounts for all monthly costs, debt paydown, and the final tax bill at the end of Year {years}.")

with insight_col2:
    tax_diff = abs(re_tax - stock_tax)
    st.info(f"**Tax Drag:** The Rental path generated **${tax_diff:,.0f}** more in tax liability than the stock path. Real estate provides leverage, but it comes with a much 'heavier' tax and commission bill upon exit.")

# --- 9. TRAJECTORY ---
st.divider()
st.subheader("📈 Pre-Tax Wealth Trajectory")
fig_traj = go.Figure()
fig_traj.add_trace(go.Scatter(x=df["Year"], y=df["RE_Equity"], name="Rental Equity", line=dict(color=PRIMARY_GOLD, width=4)))
fig_traj.add_trace(go.Scatter(x=df["Year"], y=df["Stock_Value"], name="Stock Value", line=dict(color=CHARCOAL, width=4)))
fig_traj.update_layout(height=450, template="plotly_white", yaxis=dict(tickformat="$,.0f"), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig_traj, use_container_width=True)

# --- 9. LEGAL DISCLAIMER (Optimized Spacing) ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)

st.caption("Analyst in a Pocket | Strategic Wealth Hub")