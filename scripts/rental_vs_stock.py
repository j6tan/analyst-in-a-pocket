import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
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

# --- 2. DATA RETRIEVAL (HOUSEHOLD & AFFORDABILITY) ---
prof = st.session_state.app_db.get('profile', {})
asset = st.session_state.app_db.get('target_asset', {}) 

p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')
household = f"{p1_name} & {p2_name}" if p2_name else p1_name

# T4 Intelligence: Identify higher earner for tax efficiency
p1_inc = float(prof.get('p1_inc', 0.0))
p2_inc = float(prof.get('p2_inc', 0.0))
lead_taxpayer = p1_name if p1_inc >= p2_inc else p2_name
lead_tax_rate = float(prof.get('p1_tax_rate', 35.0)) if p1_inc >= p2_inc else float(prof.get('p2_tax_rate', 35.0))

# --- 3. PERSISTENCE INITIALIZATION ---
if 'rental_vs_stock' not in st.session_state.app_db:
    st.session_state.app_db['rental_vs_stock'] = {}
rvs_data = st.session_state.app_db['rental_vs_stock']

if not rvs_data.get('initialized'):
    rvs_data.update({
        "price": float(asset.get('target_price', 800000.0)),
        "inv": float(asset.get('target_dp', 200000.0)),
        "rate": float(asset.get('interest_rate', 4.5)),
        "rent": float(asset.get('monthly_rent', 3200.0)),
        "apprec": 3.0,
        "alt_ret": 7.0,
        "years": 10,
        "tax_rate": lead_tax_rate,
        "prop_tax": 3200.0,
        "ins": 125.0,
        "strata": 450.0,
        "maint": 2000.0,
        "mgmt": 0,
        "initialized": True
    })

# --- 4. CALCULATION ENGINE ---
def run_wealth_engine(price, inv, rate, apprec, r_income, costs, alt_return, years, tax_rate):
    loan = price - inv
    m_rate = (rate/100)/12
    n_months = 25 * 12
    m_denom = ((1+m_rate)**n_months - 1)
    monthly_pi = loan * (m_rate * (1+m_rate)**n_months) / m_denom if m_denom != 0 else (loan / n_months)
    
    curr_val, curr_loan, curr_rent = price, loan, r_income
    stock_portfolio = inv + (price * 0.02) 
    stock_contributions = stock_portfolio
    
    # Calculate Year 1 "Paper Loss" for Tax Metric
    annual_int = loan * (rate/100)
    annual_opex = costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['rm'] + (r_income*12*(costs['mgmt']/100))
    annual_rent = r_income * 12
    paper_loss = max(0, (annual_int + annual_opex) - annual_rent)
    annual_tax_saving = paper_loss * (tax_rate/100)
    
    data = []
    for y in range(1, years + 1):
        for _ in range(12):
            curr_loan -= (monthly_pi - (curr_loan * m_rate))
        curr_val *= (1 + apprec/100)
        stock_portfolio *= (1 + alt_return/100)
        data.append({"Year": y, "RE_Equity": max(0, curr_val - curr_loan), "Stock_Value": stock_portfolio})

    re_selling_costs = (curr_val * 0.03) + 1500
    re_profit = curr_val - price - re_selling_costs
    re_tax = max(0, re_profit * 0.50 * (tax_rate/100))
    final_re_wealth = (curr_val - curr_loan - re_selling_costs) - re_tax
    
    stock_profit = stock_portfolio - stock_contributions
    stock_tax = max(0, stock_profit * 0.50 * (tax_rate/100))
    final_stock_wealth = stock_portfolio - stock_tax
    
    return pd.DataFrame(data), final_re_wealth, final_stock_wealth, re_tax, stock_tax, re_selling_costs, annual_tax_saving

# --- 5. STANDARDIZED HEADER ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2: st.title("Rental Property vs. Stock Portfolio")

# --- 6. STORYTELLING ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 15px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; margin-bottom: 10px; font-size: 1.5em;">💼 {p1_name} & {p2_name}’s Wealth Crossroads</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        You are debating two paths: the leveraged Rental Property or a passive Stock Portfolio. 
        This tool pulls from your <b>Affordability Tool</b> to show you which choice wins long-term.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 7. INPUTS (SURGICAL CLOUD SWAP) ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Real Estate Asset")
    price = cloud_input("Purchase Price ($)", "rental_vs_stock", "price", step=25000.0)
    inv = cloud_input("Down Payment ($)", "rental_vs_stock", "inv", step=5000.0)
    rate = cloud_input("Interest Rate (%)", "rental_vs_stock", "rate", step=0.1)
    rent = cloud_input("Monthly Rent ($)", "rental_vs_stock", "rent", step=50.0)
    
    apprec = st.slider("Annual Appreciation (%)", 0.0, 7.0, float(rvs_data.get('apprec', 3.0)), 
                       key="rental_vs_stock:apprec", on_change=sync_widget, args=("rental_vs_stock:apprec",))

    with st.expander("🛠️ Property Operating Costs"):
        tax = cloud_input("Annual Property Tax ($)", "rental_vs_stock", "prop_tax", step=100.0)
        ins = cloud_input("Monthly Insurance ($)", "rental_vs_stock", "ins", step=10.0)
        strata = cloud_input("Monthly Strata ($)", "rental_vs_stock", "strata", step=10.0)
        rm = cloud_input("Annual Maintenance ($)", "rental_vs_stock", "maint", step=100.0)
        mgmt = st.slider("Mgmt Fee (%)", 0, 10, int(rvs_data.get('mgmt', 0)),
                         key="rental_vs_stock:mgmt", on_change=sync_widget, args=("rental_vs_stock:mgmt",))

with col2:
    st.subheader("📈 Stock Portfolio")
    alt_ret = cloud_input("Portfolio Growth (%)", "rental_vs_stock", "alt_ret", step=0.5)
    years = st.select_slider("Holding Period (Years)", options=[5, 10, 15, 20, 25], 
                             value=int(rvs_data.get('years', 10)),
                             key="rental_vs_stock:years", on_change=sync_widget, args=("rental_vs_stock:years",))
    
    st.subheader("⚖️ Tax Efficiency")
    m_tax_rate = cloud_input("Marginal Tax Rate (%)", "rental_vs_stock", "tax_rate", step=1.0)
    
    st.info(f"""
        **🎯 Lead Taxpayer: {lead_taxpayer}** By holding this asset under the higher T4 earner, you can use property expenses to shelter high-bracket income.
    """)

# Execution
df, re_wealth, stock_wealth, re_tax, stock_tax, re_costs, tax_saving = run_wealth_engine(
    price, inv, rate, apprec, rent, 
    {'tax': tax, 'ins': ins, 'strata': strata, 'rm': rm, 'mgmt': mgmt},
    alt_ret, years, m_tax_rate
)

# --- 8. RESULTS & TAX METRIC ---
st.divider()
res_col1, res_col2 = st.columns([2, 1])

with res_col1:
    st.subheader("📊 Final Wealth (After Tax & Debt)")
    fig_wealth = go.Figure(data=[
        go.Bar(name='Rental (Net)', x=['Rental Path'], y=[re_wealth], marker_color=PRIMARY_GOLD, text=[f"${re_wealth:,.0f}"], textposition='auto'),
        go.Bar(name='Stocks (Net)', x=['Stock Path'], y=[stock_wealth], marker_color=CHARCOAL, text=[f"${stock_wealth:,.0f}"], textposition='auto')
    ])
    fig_wealth.update_layout(yaxis=dict(tickformat="$,.0f"), height=400, template="plotly_white", margin=dict(t=10, b=10))
    st.plotly_chart(fig_wealth, use_container_width=True)

with res_col2:
    st.subheader("🛡️ Tax Alpha")
    st.metric("Annual T4 Tax Saving", f"${tax_saving:,.0f}", help=f"Estimated annual tax refund generated by offsetting {lead_taxpayer}'s income with rental 'paper losses'.")
    st.write(f"This strategy recovers **${tax_saving:,.0f}** in cash every year from the CRA.")



# --- 9. INSIGHTS ---
st.divider()
st.subheader("🎯 Strategic Analyst Insight")
insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    diff = abs(re_wealth - stock_wealth)
    winner = "Rental Property" if re_wealth > stock_wealth else "Stock Portfolio"
    st.success(f"**The Verdict:** The **{winner}** is the superior path by **${diff:,.0f}**.")

with insight_col2:
    st.info(f"**Holding Strategy:** Holding under **{lead_taxpayer}** converts property expenses into immediate tax refunds, effectively lowering your true 'Monthly Carry' cost.")

# --- 10. TRAJECTORY ---
st.divider()
st.subheader("📈 Pre-Tax Wealth Trajectory")
fig_traj = go.Figure()
fig_traj.add_trace(go.Scatter(x=df["Year"], y=df["RE_Equity"], name="Rental Equity", line=dict(color=PRIMARY_GOLD, width=4)))
fig_traj.add_trace(go.Scatter(x=df["Year"], y=df["Stock_Value"], name="Stock Value", line=dict(color=CHARCOAL, width=4)))
fig_traj.update_layout(height=450, template="plotly_white", yaxis=dict(tickformat="$,.0f"), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig_traj, use_container_width=True)

show_disclaimer()
