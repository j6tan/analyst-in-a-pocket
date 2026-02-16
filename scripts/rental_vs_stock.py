import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget

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

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {}) 
aff_sec = st.session_state.app_db.get('affordability_second', {}) 

p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')
p1_tax = float(prof.get('p1_tax_rate', 35.0))
p2_tax = float(prof.get('p2_tax_rate', 35.0))

# --- 3. PERSISTENCE & INITIALIZATION ---
if 'rental_vs_stock' not in st.session_state.app_db:
    st.session_state.app_db['rental_vs_stock'] = {}
rvs_data = st.session_state.app_db['rental_vs_stock']

if not rvs_data.get('initialized'):
    rvs_data.update({
        "price": float(aff_sec.get('target_price', 750000.0)),
        "inv": float(aff_sec.get('down_payment', 200000.0)),
        "rate": float(aff_sec.get('contract_rate', 4.0)),
        "rent": float(aff_sec.get('manual_rent', 3500.0)),
        "apprec": 3.0,
        "stock_total_return": 8.0,
        "dividend_yield": 3.0,
        "years": 10,
        "prop_tax": 2500.0,
        "ins": 100.0,
        "strata": 300.0,
        "maint": 1200.0,
        "mgmt": 5.0,
        "stock_account": "TFSA",
        "initialized": True
    })

# --- 4. CALCULATION ENGINE ---
def run_wealth_engine(price, inv, rate, apprec, r_income, costs, total_return, s_div, years, tax_rate, acc_type):
    loan = price - inv
    m_rate = (rate/100)/12
    n_mo = 25 * 12
    m_pi = loan * (m_rate * (1+m_rate)**n_mo) / ((1+m_rate)**n_mo - 1) if loan > 0 else 0
    
    price_growth_rate = (total_return - s_div) / 100
    curr_val, curr_loan, stock_val = price, loan, inv + (price * 0.02)
    cum_re_cash = 0
    data = []
    
    for y in range(1, years + 1):
        # Rental Math
        ann_int = 0
        for _ in range(12):
            i_mo = curr_loan * m_rate
            ann_int += i_mo
            curr_loan -= (m_pi - i_mo)
        
        tax_deductibles = ann_int + costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint']
        total_cash_opex = costs['tax'] + (costs['ins']*12) + (costs['strata']*12) + costs['maint'] + (r_income*12*(costs['mgmt']/100))
        taxable_re = (r_income * 12) - tax_deductibles
        re_tax_impact = taxable_re * (tax_rate/100)
        net_re_cash = (r_income * 12) - (m_pi * 12) - total_cash_opex - re_tax_impact
        cum_re_cash += net_re_cash
        
        # Stock Math
        div_gross = stock_val * (s_div/100)
        if acc_type == "Non-Registered":
            st_tax_impact = div_gross * (tax_rate/100) * 0.5 
            reinvest_amt = div_gross - st_tax_impact
        else:
            st_tax_impact = 0 
            reinvest_amt = div_gross
            
        stock_val = (stock_val + reinvest_amt) * (1 + price_growth_rate)
        data.append({"Year": y, "RE_Cash": net_re_cash/12, "RE_Tax": re_tax_impact, "ST_Tax": st_tax_impact, "ST_Div_Mo": div_gross/12})
        curr_val *= (1 + apprec/100)

    # Sale Day
    re_sell_costs = (curr_val * 0.035) + 2000
    re_cap_gain_tax = max(0, curr_val - price - re_sell_costs) * 0.5 * (tax_rate/100)
    net_proceeds_re = curr_val - curr_loan - re_sell_costs - re_cap_gain_tax
    
    st_sell_costs = stock_val * 0.01
    if acc_type == "TFSA":
        st_tax = 0 # 100% Tax Free
    elif acc_type == "RRSP":
        st_tax = stock_val * (tax_rate/100) # Taxed as income on withdrawal
    else:
        st_profit = stock_val - (inv + (price * 0.02)) - st_sell_costs
        st_tax = max(0, st_profit) * 0.5 * (tax_rate/100) # Capital Gains 50%
        
    net_proceeds_st = stock_val - st_sell_costs - st_tax
    return pd.DataFrame(data), (net_proceeds_re + cum_re_cash), net_proceeds_st, (re_cap_gain_tax + re_sell_costs), (st_tax + st_sell_costs), net_proceeds_re, net_proceeds_st

# --- 5. INPUTS ---
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
        mgmt_pct = st.slider("Mgmt Fee (%)", 0, 10, int(rvs_data.get('mgmt', 5)))

with col2:
    st.subheader("📈 Stock Portfolio")
    st_acc = st.selectbox("Account Type", ["Non-Registered", "TFSA", "RRSP"], index=["Non-Registered", "TFSA", "RRSP"].index(rvs_data.get('stock_account', "TFSA")))
    s_total_return = cloud_input("Total Return (%)", "rental_vs_stock", "stock_total_return") 
    s_div = cloud_input("Dividend Yield (%)", "rental_vs_stock", "dividend_yield", 
                        help="Assuming dividend income gets reinvested. In Non-Reg accounts, tax is still paid annually before reinvestment.")
    
    years = st.select_slider("Horizon (Years)", options=[5, 10, 15, 20], value=int(rvs_data.get('years', 10)))
    tax_options = {f"{p1_name} ({p1_tax}%)": p1_tax, f"{p2_name} ({p2_tax}%)": p2_tax}
    tax_rate_input = tax_options[st.radio("Select Owner Marginal Tax Rate", list(tax_options.keys()), horizontal=True)]

# --- 6. SNAPSHOT ---
costs = {'tax': tax_cost, 'ins': ins_cost, 'strata': strata_cost, 'maint': maint_cost, 'mgmt': mgmt_pct}
df, re_tot, st_tot, re_leak, st_leak, re_net, st_net = run_wealth_engine(price, inv, rate, apprec, rent, costs, s_total_return, s_div, years, tax_rate_input, st_acc)

st.divider()
re_tax_annual = df.iloc[-1]['RE_Tax']
st_tax_annual = df.iloc[-1]['ST_Tax']
st_div_mo = df.iloc[-1]['ST_Div_Mo']

comp_df = pd.DataFrame({
    "Metric": ["Monthly Net Cash Flow", "Annual Tax Impact", "Net Sale Proceeds (Take-Home)", "Cost to Sell (Taxes/Fees)"],
    "🏠 Rental Path": [f"${df.iloc[-1]['RE_Cash']:,.0f}", f"{'-$' if re_tax_annual > 0 else '+$'}{abs(re_tax_annual):,.0f} {'(Tax Owed)' if re_tax_annual > 0 else '(Tax Saved)'}", f"${re_net:,.0f}", f"-${re_leak:,.0f}"],
    "📈 Stock Path": [f"${st_div_mo:,.0f} (Reinvested)", f"-${st_tax_annual:,.0f} (Tax Owed)" if st_tax_annual > 0 else "$0 (Tax-Sheltered)", f"${st_net:,.0f}", f"-${st_leak:,.0f}"]
}).set_index("Metric")
st.table(comp_df)

# --- 7. VERDICT ---
w1, w2 = st.columns(2)
w1.metric("Total Rental Wealth Outcome", f"${re_tot:,.0f}")
w2.metric("Total Stock Wealth Outcome", f"${st_tot:,.0f}")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 18px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 6px solid {PRIMARY_GOLD};">
    <h3 style="color: {CHARCOAL}; margin-top: 0; margin-bottom: 8px; font-size: 1.2em;">🏆 Strategic Verdict</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; margin-bottom: 0;">
        The <b>{"🏠 Rental Property" if re_tot > st_tot else "📈 Stock Portfolio"}</b> generates <b>${abs(re_tot - st_tot):,.0f}</b> more in total take-home wealth over {years} years.
    </p>
</div>
""", unsafe_allow_html=True)

show_disclaimer()
