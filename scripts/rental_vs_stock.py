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

# --- 2. DATA RETRIEVAL (STRICT LINKING TO AFFORDABILITY SECONDARY) ---
prof = st.session_state.app_db.get('profile', {}) 
aff_sec = st.session_state.app_db.get('affordability_second', {}) 

p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')
household = f"{p1_name} & {p2_name}" if p2_name else p1_name

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

# --- 4. PRE-CALCULATION FOR TAX STRATEGY ---
est_loan = rvs_data['price'] - rvs_data['inv']
est_annual_int = est_loan * (rvs_data['rate']/100)
est_annual_opex = rvs_data['prop_tax'] + (rvs_data['ins']*12) + (rvs_data['strata']*12) + rvs_data['maint']
est_taxable_inc = (rvs_data['rent'] * 12) - est_annual_int - est_annual_opex

if est_taxable_inc > 0:
    rec_name, rec_rate, rec_reason = lower_name, lower_rate, "Profit Minimization (Hold under lower earner)."
else:
    rec_name, rec_rate, rec_reason = higher_name, higher_rate, "Loss Maximization (Maximize T4 refunds)."

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
        # Rental
        ann_int = 0
        for _ in range(12):
            i_mo = curr_loan * m_rate
            ann_int += i_mo
            curr_loan -= (m_pi - i_mo)
        
        ann_opex = costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint'] + (r_income*12*(costs['mgmt']/100))
        taxable_re = (r_income * 12) - ann_int - ann_opex
        re_tax_impact = taxable_re * (tax_rate/100)
        net_re_cash = (r_income * 12) - (m_pi * 12) - ann_opex - re_tax_impact
        cum_re_cash += net_re_cash
        
        # Stock
        div_gross = stock_val * (s_div/100)
        if acc_type == "TFSA": div_tax = 0
        elif acc_type == "RRSP": div_tax = 0
        else: div_tax = div_gross * (tax_rate/100) * 0.5 
            
        net_st_cash = div_gross - div_tax
        cum_st_cash += net_st_cash
        
        curr_val *= (1 + apprec/100)
        stock_val *= (1 + s_growth/100)
        data.append({"Year": y, "RE_Equity": max(0, curr_val - curr_loan), "Stock_Value": stock_val, 
                     "RE_Cash": net_re_cash/12, "Stock_Cash": net_st_cash/12})

    re_sell_fees = (curr_val * 0.035) + 2000
    re_cap_gain_tax = max(0, curr_val - price - re_sell_fees) * 0.5 * (tax_rate/100)
    final_re = (curr_val - curr_loan - re_sell_fees - re_cap_gain_tax) + cum_re_cash

    st_sell_fees = stock_val * 0.01
    st_profit = stock_val - (inv + (price*0.02)) - st_sell_fees
    if acc_type == "TFSA": st_tax = 0
    elif acc_type == "RRSP": st_tax = stock_val * (tax_rate/100) 
    else: st_tax = max(0, st_profit) * 0.5 * (tax_rate/100)
        
    final_st = (stock_val - st_sell_fees - st_tax) + cum_st_cash
    return pd.DataFrame(data), final_re, final_st, (re_cap_gain_tax + re_sell_fees), (st_tax + st_sell_fees), curr_val, stock_val, re_tax_impact

# --- 6. INPUTS ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Real Estate Asset")
    price = cloud_input("Purchase Price ($)", "rental_vs_stock", "price")
    inv = cloud_input("Down Payment ($)", "rental_vs_stock", "inv")
    rate = cloud_input("Interest Rate (%)", "rental_vs_stock", "rate")
    rent = cloud_input("Monthly Rent ($)", "rental_vs_stock", "rent")
    apprec = st.slider("Appreciation (%)", 0.0, 7.0, float(rvs_data.get('apprec', 3.0)))

    with st.expander("🛠️ Property Operating Costs"):
        tax_cost = cloud_input("Annual Property Tax ($)", "rental_vs_stock", "prop_tax")
        ins_cost = cloud_input("Monthly Insurance ($)", "rental_vs_stock", "ins")
        strata_cost = cloud_input("Monthly Strata ($)", "rental_vs_stock", "strata")
        maint_cost = cloud_input("Annual Maintenance ($)", "rental_vs_stock", "maint")
        mgmt_pct = st.slider("Mgmt Fee (%)", 0, 10, int(rvs_data.get('mgmt', 0)))

with col2:
    st.subheader("📈 Stock Portfolio")
    acc_options = ["Non-Registered", "TFSA", "RRSP"]
    st_acc = st.selectbox("Account Type", acc_options, index=acc_options.index(rvs_data.get('stock_account', "Non-Registered")))
    s_growth = cloud_input("Price Growth (%)", "rental_vs_stock", "stock_growth")
    s_div = cloud_input("Dividend Yield (%)", "rental_vs_stock", "dividend_yield")
    years = st.select_slider("Horizon (Years)", options=[5, 10, 15, 20], value=int(rvs_data.get('years', 10)))
    tax_rate_input = cloud_input("Owner Marginal Tax Rate (%)", "rental_vs_stock", "tax_rate")
    
    st.info(f"**🎯 Strategic Recommendation:** Hold under **{rec_name}**. \n\n*Reason: {rec_reason}*")

# EXECUTION
costs = {'tax': tax_cost, 'ins': ins_cost, 'strata': strata_cost, 'maint': maint_cost, 'mgmt': mgmt_pct}
df, re_tot, st_tot, re_sunk, st_sunk, re_p, st_p, yr1_re_tax = run_wealth_engine(price, inv, rate, apprec, rent, costs, s_growth, s_div, years, tax_rate_input, st_acc)

# --- 7. SIDE-BY-SIDE SNAPSHOT ---
st.divider()
st.subheader(f"📊 Year {years} Side-by-Side Comparison")

# Custom Table for Comparison
comparison_data = {
    "Metric": ["Monthly Net Cash Flow", "Gross Asset Value (Sale Price)", "Total Sunk Costs (Taxes/Fees)"],
    "🏠 Rental Path": [f"${df.iloc[-1]['RE_Cash']:,.0f}", f"${re_p:,.0f}", f"-${re_sunk:,.0f}"],
    "📈 Stock Path": [f"${df.iloc[-1]['Stock_Cash']:,.0f}", f"${st_p:,.0f}", f"-${st_sunk:,.0f}"]
}
st.table(pd.DataFrame(comparison_data).set_index('Metric'))

# --- 8. TAX IMPLICATION SUMMARY ---
tc1, tc2 = st.columns(2)
with tc1:
    if yr1_re_tax < 0:
        st.success(f"🛡️ **Rental T4 Impact:** You receive an estimated **${abs(yr1_re_tax):,.0f}/yr** tax refund by offsetting **{rec_name}**'s income.")
    else:
        st.warning(f"💸 **Rental T4 Impact:** Holding this property adds **${yr1_re_tax:,.0f}/yr** to **{rec_name}**'s annual tax bill.")

with tc2:
    if st_acc == "TFSA":
        st.success("✨ **Stock Tax Impact:** 100% Tax-Free. No tax on dividends or capital gains.")
    elif st_acc == "RRSP":
        st.info(f"⏳ **Stock Tax Impact:** Tax-deferred. You will owe **${(st_p * (tax_rate_input/100)):,.0f}** upon full withdrawal in Year {years}.")
    else:
        st.warning("💸 **Stock Tax Impact:** Tax drag from capital gains and dividends reduces your annual return.")

# --- 9. TOTAL WEALTH ---
st.divider()
st.subheader("🏆 Total Wealth Outcome (Cash Flow + Net Sale)")
fig = go.Figure(data=[
    go.Bar(name='Rental Path', x=['Rental Path'], y=[re_tot], marker_color=PRIMARY_GOLD, text=[f"${re_tot:,.0f}"], textposition='auto'),
    go.Bar(name='Stock Path', x=['Stock Path'], y=[st_tot], marker_color=CHARCOAL, text=[f"${st_tot:,.0f}"], textposition='auto')
])
st.plotly_chart(fig, use_container_width=True)

show_disclaimer()
