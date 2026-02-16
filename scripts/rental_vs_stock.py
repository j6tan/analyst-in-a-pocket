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
BORDER_GREY = "#DEE2E6" # Fixed the missing variable

# --- 2. DATA RETRIEVAL (STRICT LINKING) ---
prof = st.session_state.app_db.get('profile', {}) 
aff_sec = st.session_state.app_db.get('affordability_second', {}) 

p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

# T4 Intelligence
p1_inc = float(prof.get('p1_t4', 0.0)) + float(prof.get('p1_bonus', 0.0))
p2_inc = float(prof.get('p2_t4', 0.0)) + float(prof.get('p2_bonus', 0.0))
p1_tax = float(prof.get('p1_tax_rate', 35.0))
p2_tax = float(prof.get('p2_tax_rate', 35.0))

if p1_inc >= p2_inc:
    higher_name, higher_rate = p1_name, p1_tax
    lower_name, lower_rate = p2_name, p2_tax
else:
    higher_name, higher_rate = p2_name, p2_tax
    lower_name, lower_rate = p1_name, p1_tax

# --- 3. PERSISTENCE & INITIALIZATION ---
if 'rental_vs_stock' not in st.session_state.app_db:
    st.session_state.app_db['rental_vs_stock'] = {}
rvs_data = st.session_state.app_db['rental_vs_stock']

if not rvs_data.get('initialized'):
    rvs_data.update({
        "price": float(aff_sec.get('target_price', 800000.0)),
        "inv": float(aff_sec.get('down_payment', 200000.0)),
        "rate": float(aff_sec.get('contract_rate', 4.5)),
        "rent": float(aff_sec.get('manual_rent', 3200.0)),
        "apprec": 3.0,
        "stock_growth": 5.0,
        "dividend_yield": 2.0,
        "years": 10,
        "prop_tax": float(aff_sec.get('annual_prop_tax', 3200.0)),
        "ins": float(aff_sec.get('insurance_mo', 125.0)),
        "strata": float(aff_sec.get('strata_mo', 450.0)),
        "maint": float(aff_sec.get('rm_mo', 200.0)) * 12,
        "mgmt": float(aff_sec.get('mgmt_pct', 0.0)),
        "stock_account": "Non-Registered",
        "initialized": True
    })

# --- 4. DYNAMIC TAX RECOMMENDATION ---
est_loan = rvs_data['price'] - rvs_data['inv']
est_annual_int = est_loan * (rvs_data['rate']/100)
est_annual_opex = rvs_data['prop_tax'] + (rvs_data['ins']*12) + (rvs_data['strata']*12) + rvs_data['maint']
est_taxable_inc = (rvs_data['rent'] * 12) - est_annual_int - est_annual_opex

if est_taxable_inc > 0:
    rec_name, rec_rate, rec_reason = lower_name, lower_rate, "Profit Minimization (Lower Tax Bill)."
else:
    rec_name, rec_rate, rec_reason = higher_name, higher_rate, "Loss Maximization (Higher T4 Refund)."

if not rvs_data.get('tax_set'):
    rvs_data['tax_rate'] = rec_rate
    rvs_data['tax_set'] = True

# --- 5. CALCULATION ENGINE ---
def run_wealth_engine(price, inv, rate, apprec, r_income, costs, s_growth, s_div, years, tax_rate, acc_type):
    loan = price - inv
    m_rate = (rate/100)/12
    n_mo = 25 * 12
    m_pi = loan * (m_rate * (1+m_rate)**n_mo) / ((1+m_rate)**n_mo - 1) if loan > 0 else 0
    
    curr_val, curr_loan, stock_val = price, loan, inv + (price * 0.02)
    cum_re_cash, cum_st_cash = 0, 0
    data = []
    
    for y in range(1, years + 1):
        # 1. Rental Path Logic
        ann_int = 0
        for _ in range(12):
            i_mo = curr_loan * m_rate
            ann_int += i_mo
            curr_loan -= (m_pi - i_mo)
        
        # User Logic: Deductibles = Interest + Tax + Ins + Strata + R&M
        tax_deductibles = ann_int + costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint']
        total_cash_opex = costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint'] + (r_income*12*(costs['mgmt']/100))
        
        taxable_re = (r_income * 12) - tax_deductibles
        re_tax_impact = taxable_re * (tax_rate/100) 
        
        net_re_cash = (r_income * 12) - (m_pi * 12) - total_cash_opex - re_tax_impact
        cum_re_cash += net_re_cash
        
        # 2. Stock Path Logic
        div_gross = stock_val * (s_div/100)
        if acc_type == "Non-Registered":
            st_tax_impact = div_gross * (tax_rate/100) * 0.5 # Div Tax Credit approx
        else:
            st_tax_impact = 0 
            
        net_st_cash = div_gross - st_tax_impact
        cum_st_cash += net_st_cash
        
        curr_val *= (1 + apprec/100)
        stock_val *= (1 + s_growth/100)
        
        data.append({
            "Year": y, "RE_Equity": max(0, curr_val - curr_loan), "Stock_Value": stock_val, 
            "RE_Cash": net_re_cash/12, "Stock_Cash": net_st_cash/12,
            "RE_Tax": re_tax_impact, "ST_Tax": st_tax_impact
        })

    # Sale Proceeds - Rental
    re_sell_costs = (curr_val * 0.035) + 2000 
    re_cap_gain_tax = max(0, curr_val - price - re_sell_costs) * 0.5 * (tax_rate/100)
    net_proceeds_re = curr_val - curr_loan - re_sell_costs - re_cap_gain_tax
    final_re_wealth = net_proceeds_re + cum_re_cash

    # Sale Proceeds - Stock
    st_sell_costs = stock_val * 0.01
    st_profit = stock_val - (inv + (price*0.02)) - st_sell_costs
    if acc_type == "TFSA": st_tax = 0
    elif acc_type == "RRSP": st_tax = stock_val * (tax_rate/100) 
    else: st_tax = max(0, st_profit) * 0.5 * (tax_rate/100)
    
    net_proceeds_st = stock_val - st_sell_costs - st_tax
    final_stock_wealth = net_proceeds_st + cum_st_cash
    
    return pd.DataFrame(data), final_re_wealth, final_stock_wealth, (re_cap_gain_tax + re_sell_fees), (st_tax + st_sell_fees) if 're_sell_fees' in locals() else (re_cap_gain_tax + re_sell_costs), (st_tax + st_sell_costs), net_proceeds_re, net_proceeds_st

# Calculation Fix for Return Values
def run_wealth_engine_fixed(price, inv, rate, apprec, r_income, costs, s_growth, s_div, years, tax_rate, acc_type):
    loan = price - inv
    m_rate = (rate/100)/12
    n_mo = 25 * 12
    m_pi = loan * (m_rate * (1+m_rate)**n_mo) / ((1+m_rate)**n_mo - 1) if loan > 0 else 0
    curr_val, curr_loan, stock_val = price, loan, inv + (price * 0.02)
    cum_re_cash, cum_st_cash = 0, 0
    data = []
    for y in range(1, years + 1):
        ann_int = 0
        for _ in range(12):
            i_mo = curr_loan * m_rate
            ann_int += i_mo
            curr_loan -= (m_pi - i_mo)
        tax_deductibles = ann_int + costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint']
        total_opex = costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint'] + (r_income*12*(costs['mgmt']/100))
        taxable_re = (r_income * 12) - tax_deductibles
        re_tax_impact = taxable_re * (tax_rate/100)
        net_re_cash = (r_income * 12) - (m_pi * 12) - total_opex - re_tax_impact
        cum_re_cash += net_re_cash
        div_gross = stock_val * (s_div/100)
        st_tax_impact = div_gross * (tax_rate/100) * 0.5 if acc_type == "Non-Registered" else 0
        net_st_cash = div_gross - st_tax_impact
        cum_st_cash += net_st_cash
        curr_val *= (1 + apprec/100)
        stock_val *= (1 + s_growth/100)
        data.append({"Year": y, "RE_Cash": net_re_cash/12, "Stock_Cash": net_st_cash/12, "RE_Tax": re_tax_impact, "ST_Tax": st_tax_impact, "RE_Equity": max(0, curr_val-curr_loan), "Stock_Value": stock_val})
    re_sell_costs = (curr_val * 0.035) + 2000
    re_cap_gain_tax = max(0, curr_val - price - re_sell_costs) * 0.5 * (tax_rate/100)
    net_proceeds_re = curr_val - curr_loan - re_sell_costs - re_cap_gain_tax
    st_sell_costs = stock_val * 0.01
    st_profit = stock_val - (inv + (price*0.02)) - st_sell_costs
    st_tax = 0 if acc_type == "TFSA" else (stock_val * (tax_rate/100) if acc_type == "RRSP" else max(0, st_profit) * 0.5 * (tax_rate/100))
    net_proceeds_st = stock_val - st_sell_costs - st_tax
    return pd.DataFrame(data), (net_proceeds_re + cum_re_cash), (net_proceeds_st + cum_st_cash), (re_cap_gain_tax + re_sell_costs), (st_tax + st_sell_costs), net_proceeds_re, net_proceeds_st

# --- 6. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Real Estate Asset")
    price = cloud_input("Purchase Price ($)", "rental_vs_stock", "price")
    inv = cloud_input("Down Payment ($)", "rental_vs_stock", "inv")
    rate = cloud_input("Interest Rate (%)", "rental_vs_stock", "rate")
    rent = cloud_input("Monthly Rent ($)", "rental_vs_stock", "rent")
    apprec = st.slider("Appreciation (%)", 0.0, 7.0, float(rvs_data.get('apprec', 3.0)))
    with st.expander("🛠️ Operating Costs"):
        tax_cost = cloud_input("Annual Property Tax ($)", "rental_vs_stock", "prop_tax")
        ins_cost = cloud_input("Monthly Insurance ($)", "rental_vs_stock", "ins")
        strata_cost = cloud_input("Monthly Strata ($)", "rental_vs_stock", "strata")
        maint_cost = cloud_input("Annual Maintenance ($)", "rental_vs_stock", "maint")
        mgmt_pct = st.slider("Mgmt Fee (%)", 0, 10, int(rvs_data.get('mgmt', 0)))

with col2:
    st.subheader("📈 Stock Portfolio")
    st_acc = st.selectbox("Account Type", ["Non-Registered", "TFSA", "RRSP"], index=["Non-Registered", "TFSA", "RRSP"].index(rvs_data.get('stock_account', "Non-Registered")))
    s_growth = cloud_input("Price Growth (%)", "rental_vs_stock", "stock_growth")
    s_div = cloud_input("Dividend Yield (%)", "rental_vs_stock", "dividend_yield")
    years = st.select_slider("Horizon (Years)", options=[5, 10, 15, 20], value=int(rvs_data.get('years', 10)))
    tax_rate_input = cloud_input("Owner Marginal Tax Rate (%)", "rental_vs_stock", "tax_rate")
    st.info(f"**🎯 Strategy:** Hold under **{rec_name}** to minimize tax bill / maximize refund.")

# --- 7. EXECUTION ---
costs = {'tax': tax_cost, 'ins': ins_cost, 'strata': strata_cost, 'maint': maint_cost, 'mgmt': mgmt_pct}
df, re_tot, st_tot, re_leak, st_leak, re_net, st_net = run_wealth_engine_fixed(price, inv, rate, apprec, rent, costs, s_growth, s_div, years, tax_rate_input, st_acc)

# --- 8. COMPARISON TABLE ---
st.divider()
st.subheader(f"📊 Year {years} Side-by-Side Comparison")
re_tax_annual = df.iloc[-1]['RE_Tax']
st_tax_annual = df.iloc[-1]['ST_Tax']

comp_df = pd.DataFrame({
    "Metric": ["Monthly Net Cash Flow", "Annual Tax Implication", "Net Sale Proceeds (Take-Home)", "Cost to Sell (Exit Tax/Fees)"],
    "🏠 Rental Path": [f"${df.iloc[-1]['RE_Cash']:,.0f}", f"{'-$' if re_tax_annual > 0 else '+$'}{abs(re_tax_annual):,.0f} {'Bill' if re_tax_annual > 0 else 'Refund'}", f"${re_net:,.0f}", f"-${re_leak:,.0f}"],
    "📈 Stock Path": [f"${df.iloc[-1]['Stock_Cash']:,.0f}", f"-${st_tax_annual:,.0f} Bill" if st_tax_annual > 0 else "$0 (Tax-Sheltered)", f"${st_net:,.0f}", f"-${st_leak:,.0f}"]
}).set_index("Metric")
st.table(comp_df)

# --- 9. VERDICT ---
winner = "🏠 Rental Path" if re_tot > st_tot else "📈 Stock Path"
st.markdown(f"""
<div style="background-color: {CHARCOAL}; padding: 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; text-align: center;">
    <h2 style="color: {PRIMARY_GOLD}; margin-top: 0;">🏆 Strategic Verdict</h2>
    <p style="color: white; font-size: 1.3em;">The <b>{winner}</b> generates <b>${abs(re_tot - st_tot):,.0f}</b> more in total take-home wealth.</p>
</div>
""", unsafe_allow_html=True)

# --- 10. WEALTH CHART ---
st.divider()
st.subheader("🏆 Total Take-Home Wealth")
fig = go.Figure(data=[
    go.Bar(name='Rental', x=['Rental Path'], y=[re_tot], marker_color=PRIMARY_GOLD, text=[f"${re_tot:,.0f}"], textposition='auto'),
    go.Bar(name='Stock', x=['Stock Path'], y=[st_tot], marker_color=CHARCOAL, text=[f"${st_tot:,.0f}"], textposition='auto')
])
st.plotly_chart(fig, use_container_width=True)

show_disclaimer()
