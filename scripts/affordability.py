import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import math
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return float(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
province = prof.get('province', 'Ontario')
name1 = prof.get('p1_name', 'Primary Client')
name2 = prof.get('p2_name', '')
is_renter = prof.get('housing_status') == "Renting"
household = f"{name1} and {name2}" if name2 else name1

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}}

intel = load_market_intel()

# --- 3. CALCULATORS ---
def calculate_ltt_and_fees(price, province_val, is_fthb, is_toronto=False):
    tax_rules = intel.get("tax_rules", {})
    if not tax_rules: return 0, 0
    prov_rules = tax_rules.get(province_val, [])
    total_prov_tax, prev_h = 0, 0
    for rule in prov_rules:
        if price > prev_h:
            taxable = min(price, rule["threshold"]) - prev_h
            total_prov_tax += taxable * rule["rate"]
            prev_h = rule["threshold"]
    total_muni_tax = 0
    if is_toronto and province_val == "Ontario":
        muni_rules = tax_rules.get("Toronto_Municipal", [])
        prev_m = 0
        for rule in muni_rules:
            if price > prev_m:
                taxable = min(price, rule["threshold"]) - prev_m
                total_muni_tax += taxable * rule["rate"]
                prev_m = rule["threshold"]
    rebates = tax_rules.get("rebates", {})
    total_rebate = 0
    if is_fthb:
        if province_val == "Ontario":
            total_rebate += min(total_prov_tax, rebates.get("ON_FTHB_Max", 4000))
            if is_toronto: total_rebate += min(total_muni_tax, rebates.get("Toronto_FTHB_Max", 4475))
        elif province_val == "BC":
            fthb_limit = rebates.get("BC_FTHB_Threshold", 835000)
            if price <= fthb_limit: total_rebate = total_prov_tax
    return total_prov_tax + total_muni_tax, total_rebate

def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

def solve_max_affordability(income_annual, debts_monthly, stress_rate, tax_rate):
    m_inc = income_annual / 12
    HEAT_FACTOR, TAX_FACTOR = 0.0002, tax_rate / 12
    ALPHA = HEAT_FACTOR + TAX_FACTOR
    r_mo = (stress_rate / 100) / 12
    K = (r_mo * (1 + r_mo)**300) / ((1 + r_mo)**300 - 1) if r_mo > 0 else 1/300
    budget = min(m_inc * 0.39, (m_inc * 0.44) - debts_monthly)
    p3, p2, p1 = budget/(0.8*K+ALPHA), (budget-(25000*K))/(0.9*K+ALPHA), budget/(0.95*K+ALPHA)
    if p3 >= 1000000: fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: fp, fd = min(p2, 999999), 25000 + (min(p2, 999999) - 500000) * 0.10
    else: fp, fd = min(p1, 499999), min(p1, 499999) * 0.05
    return fp, fd

# --- 4. PROFILE SUMMARIES ---
t4_sum = float(prof.get('p1_t4', 0)) + float(prof.get('p2_t4', 0)) + float(prof.get('p1_pension', 0)) + float(prof.get('p2_pension', 0))
bonus_sum = float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))
rental_sum = float(prof.get('inv_rental_income', 0))
debt_sum = float(prof.get('car_loan', 0)) + float(prof.get('student_loan', 0)) + float(prof.get('cc_pmt', 0)) + (float(prof.get('loc_balance', 0)) * 0.03)

# --- 5. INITIALIZE SCENARIO ---
if 'affordability' not in st.session_state.app_db:
    st.session_state.app_db['affordability'] = {}
aff = st.session_state.app_db['affordability']

if aff.get('rental', 0) == 0: aff['rental'] = rental_sum
if aff.get('combined_t4', 0) == 0: aff['combined_t4'] = t4_sum
if aff.get('combined_bonus', 0) == 0: aff['combined_bonus'] = bonus_sum
if aff.get('combined_debt', 0) == 0: aff['combined_debt'] = debt_sum

if aff.get('bank_rate', 0) == 0:
    TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
    tr = TAX_DEFAULTS.get(province, 0.0075)
    max_p, min_d = solve_max_affordability(t4_sum + bonus_sum + (rental_sum * 0.8), debt_sum, 6.26, tr)
    aff.update({'bank_rate': 4.26, 'down_payment': custom_round_up(min_d + 2000), 'prop_taxes': custom_round_up(max_p * tr), 
                'heat': custom_round_up(max_p * 0.0002), 'loan_cap': 0.0})
    if st.session_state.get("is_logged_in"):
        supabase.table("user_vault").upsert({"id": st.session_state.username, "data": st.session_state.app_db}).execute()

# --- 6. PRE-CALCULATION FOR CAP NOTE ---
monthly_inc_pre = (aff.get('combined_t4', 0) + aff.get('combined_bonus', 0) + (aff.get('rental', 0)*0.80)) / 12
s_rate_pre = max(5.25, aff.get('bank_rate', 4.26) + 2.0)
gds_pre = (monthly_inc_pre * 0.39) - aff.get('heat', 0) - (aff.get('prop_taxes', 0)/12)
tds_pre = (monthly_inc_pre * 0.44) - aff.get('heat', 0) - (aff.get('prop_taxes', 0)/12) - aff.get('combined_debt', 0)
max_pi_pre = min(gds_pre, tds_pre)
r_mo_pre = (s_rate_pre/100)/12
qual_loan_pre = custom_round_up(max_pi_pre * (1 - (1+r_mo_pre)**-300) / r_mo_pre) if r_mo_pre > 0 else 0.0

# --- 7. HEADER ---
st.title("Mortgage Affordability Analysis")
st.markdown(f"""<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD};">
    <h3 style="margin-top:0;">🚀 {household}: Planning Your Move</h3>
    <p style="margin-bottom:0;">Mapping out the math for your next home in <b>{province}</b>.</p>
</div>""", unsafe_allow_html=True)

# --- 8. UNDERWRITING ASSUMPTIONS ---
st.subheader("⚙️ Underwriting Assumptions")
uw_col1, uw_col2, uw_col3 = st.columns(3)
with uw_col1:
    c_rate = cloud_input("Bank Contract Rate %", "affordability", "bank_rate", step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.markdown(f"**Qualifying Rate:** {s_rate:.2f}%")
with uw_col2:
    f_dp = cloud_input("Down Payment ($)", "affordability", "down_payment", step=1000.0)
    loan_cap = cloud_input("Manual Loan Cap (Optional)", "affordability", "loan_cap", step=5000.0)
    st.caption(f"Note: Max Qualified Loan: **${qual_loan_pre:,.0f}**")
with uw_col3:
    f_ptax = cloud_input("Annual Property Taxes", "affordability", "prop_taxes", step=100.0)
    f_heat = cloud_input("Monthly Heat", "affordability", "heat", step=10.0)
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], 
                             index=0 if aff.get('prop_type') == "House / Freehold" else 1,
                             key="affordability:prop_type", on_change=sync_widget, args=("affordability:prop_type",))
    strata = cloud_input("Monthly Strata", "affordability", "strata", step=10.0) if prop_type == "Condo / Townhome" else 0

st.divider()

# --- 9. INCOME & DEBT ---
col_1, col_2, col_3 = st.columns([1.2, 1.2, 1.5])
with col_1:
    st.subheader("💰 Income Summary")
    i_t4 = cloud_input("Combined T4 Income", "affordability", "combined_t4", step=1000.0)
    i_bonus = cloud_input("Total Additional Income", "affordability", "combined_bonus", step=500.0)
    i_rental = cloud_input("Joint Rental Income", "affordability", "rental", step=100.0)
    total_qualifying = i_t4 + i_bonus + (i_rental * 0.80)
    st.markdown(f"**Qualifying Income:** ${total_qualifying:,.0f}")

with col_2:
    st.subheader("💳 Debt & Status")
    i_debt = cloud_input("Monthly Debts", "affordability", "combined_debt", step=50.0)
    f_fthb = st.checkbox("First-Time Home Buyer?", value=aff.get('is_fthb', False), key="affordability:is_fthb", on_change=sync_widget, args=("affordability:is_fthb",))
    f_toronto = st.checkbox("Toronto Limits?", key="affordability:is_toronto") if province == "Ontario" else False

with col_3:
    st.info("""
    **💡 Underwriting Insights:**
    * **T4:** Qualified at **100%** of base salary.
    * **Additional Income:** Bonuses use a **2-year average**.
    * **Rental Income:** Typically 'haircut' to **80%** for expenses.
    * **Liabilities:** LOCs stressed at **3% of limit**.
    """)

# --- 10. THE DASHBOARD (RELOADED) ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - f_heat - (f_ptax/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - f_heat - (f_ptax/12) - (strata*0.5) - i_debt
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo_stress = (s_rate/100)/12
    raw_loan = max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress if r_mo_stress > 0 else max_pi_stress * 300
    
    # Apply Cap
    qualified_loan = custom_round_up(raw_loan)
    loan_amt = min(qualified_loan, loan_cap) if loan_cap > 0 else qualified_loan
    max_purchase = loan_amt + f_dp
    
    # Math for display
    r_mo_contract = (c_rate/100)/12
    contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300) if r_mo_contract > 0 else loan_amt / 300

    # Validation check
    min_required = calculate_min_downpayment(max_purchase)
    if f_dp < (min_required - 0.99):
        st.error(f"#### 🛑 Down Payment Too Low")
        st.markdown(f"""<div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px;">
            Min. required for <b>${max_purchase:,.0f}</b> is <b>${min_required:,.0f}</b>. Use the <b>Manual Loan Cap</b> to target a lower price.
        </div>""", unsafe_allow_html=True)
        st.stop()

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase", f"${max_purchase:,.0f}")
    m2.metric("Max Loan", f"${loan_amt:,.0f}")
    m3.metric("Monthly P&I", f"${contract_pi:,.0f}")
    m4.metric("Stress P&I", f"${max_pi_stress:,.0f}")

    r_c1, r_c2 = st.columns([2, 1.2])
    with r_c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=max_purchase, gauge={'axis': {'range': [0, max_purchase*1.5]}, 'bar': {'color': PRIMARY_GOLD}}))
        fig.update_layout(height=350, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with r_c2:
        st.subheader("⚖️ Cash-to-Close")
        total_tax, total_rebate = calculate_ltt_and_fees(max_purchase, province, f_fthb, f_toronto)
        total_closing = total_tax - total_rebate + 2350
        total_cash = f_dp + total_closing
        monthly_cost = contract_pi + (f_ptax/12) + f_heat + strata
        
        breakdown = [
            {"Item": "Down Payment", "Cost": f_dp},
            {"Item": "Land Transfer Tax", "Cost": total_tax},
            {"Item": "FTHB Rebate", "Cost": -total_rebate},
            {"Item": "Legal / Misc", "Cost": 2350}
        ]
        st.table(pd.DataFrame(breakdown).assign(Cost=lambda x: x['Cost'].map('${:,.0f}'.format)))
        
        st.markdown(f"""
        <div style="background-color: {PRIMARY_GOLD}; color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
            <p style="margin: 0; font-size: 0.8em;">TOTAL CASH TO CLOSE</p>
            <p style="margin: 0; font-size: 1.5em; font-weight: 800;">${total_cash:,.0f}</p>
        </div>
        <div style="background-color: #C0C0C0; color: white; padding: 10px; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 0.8em;">MONTHLY HOME COST</p>
            <p style="margin: 0; font-size: 1.5em; font-weight: 800;">${monthly_cost:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.error("Approval amount is $0.")

show_disclaimer()


