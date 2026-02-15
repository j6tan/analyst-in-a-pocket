import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import math
from style_utils import inject_global_css
from data_handler import cloud_input, sync_widget

# 1. Inject CSS
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

# --- 2. DATA RETRIEVAL & SMART SUMS ---
prof = st.session_state.app_db.get('profile', {})
province = prof.get('province', 'Ontario')
name1 = prof.get('p1_name', 'Primary Client')
name2 = prof.get('p2_name', '')
is_renter = prof.get('housing_status') == "Renting"
household = f"{name1} and {name2}" if name2 else name1

# FIX: Correctly sum all income sources from the Profile
t4_sum = float(prof.get('p1_t4', 0)) + float(prof.get('p2_t4', 0)) + float(prof.get('p1_pension', 0)) + float(prof.get('p2_pension', 0))
bonus_sum = float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0)) + float(prof.get('other_income', 0))
rental_sum = float(prof.get('inv_rental_income', 0))

# FIX: Correctly sum all debts including the 3% LOC Stress
debt_sum = (
    float(prof.get('car_loan', 0)) + 
    float(prof.get('student_loan', 0)) + 
    float(prof.get('cc_pmt', 0)) + 
    float(prof.get('support_pmt', 0)) + 
    float(prof.get('other_debt', 0)) + 
    (float(prof.get('loc_balance', 0)) * 0.03)
)

# --- 3. SMART DEFAULT LOGIC ---
def calculate_min_downpayment(price):
    if price >= 1000000: return price * 0.20
    elif price <= 500000: return price * 0.05
    else: return (500000 * 0.05) + ((price - 500000) * 0.10)

def solve_max_affordability(income_annual, debts_monthly, stress_rate, tax_rate):
    m_inc = income_annual / 12
    HEAT_FACTOR, TAX_FACTOR = 0.0002, tax_rate / 12
    ALPHA = HEAT_FACTOR + TAX_FACTOR
    r_mo = (stress_rate / 100) / 12
    # Zero Division Safety
    if r_mo > 0:
        K = (r_mo * (1 + r_mo)**300) / ((1 + r_mo)**300 - 1)
    else:
        K = 1/300
    
    budget = min(m_inc * 0.39, (m_inc * 0.44) - debts_monthly)
    p3 = budget / (0.80 * K + ALPHA)
    p2 = (budget - (25000 * K)) / (0.90 * K + ALPHA)
    p1 = budget / (0.95 * K + ALPHA)
    
    if p3 >= 1000000: fp, fd = p3, p3 * 0.20
    elif p2 >= 500000: 
        fp = min(p2, 999999)
        fd = 25000 + (fp - 500000) * 0.10
    else: 
        fp = min(p1, 499999)
        fd = fp * 0.05
    return fp, fd

# --- 4. INITIALIZE SCENARIO (THE FIX) ---
if 'affordability' not in st.session_state.app_db:
    st.session_state.app_db['affordability'] = {}

aff = st.session_state.app_db['affordability']

# If values are 0 or missing, we trigger the "Smart Default"
if aff.get('bank_rate', 0) == 0:
    TAX_DEFAULTS = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
    tr = TAX_DEFAULTS.get(province, 0.0075)
    s_val = 6.26
    
    max_p, min_d = solve_max_affordability(t4_sum + bonus_sum + (rental_sum * 0.8), debt_sum, s_val, tr)
    
    # Push smart values to the Cloud Vault immediately
    aff['bank_rate'] = 4.26
    aff['down_payment'] = custom_round_up(min_d + 2000)
    aff['prop_taxes'] = custom_round_up(max_p * tr)
    aff['heat'] = custom_round_up(max_p * 0.0002)
    # Carry over profile sums
    aff['combined_t4'] = t4_sum
    aff['combined_bonus'] = bonus_sum
    aff['combined_debt'] = debt_sum

# --- 5. HEADER & STORY ---
st.title("Mortgage Affordability Analysis")
st.markdown(f"""<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD};">
    <h3>🚀 {household}: From Renting to Ownership</h3>
    <p>Mapping out the math needed for <b>{province}</b>.</p>
</div>""", unsafe_allow_html=True)

# --- 6. UNDERWRITING ASSUMPTIONS ---
st.subheader("⚙️ Underwriting Assumptions")
uw_col1, uw_col2, uw_col3 = st.columns(3)
with uw_col1:
    c_rate = cloud_input("Bank Contract Rate %", "affordability", "bank_rate", step=0.01)
    s_rate = max(5.25, c_rate + 2.0)
    st.markdown(f"**Qualifying Rate:** {s_rate:.2f}%")
with uw_col2:
    f_dp = cloud_input("Down Payment ($)", "affordability", "down_payment", step=1000.0)
    f_ptax = cloud_input("Annual Property Taxes", "affordability", "prop_taxes", step=100.0)
with uw_col3:
    f_heat = cloud_input("Monthly Heat", "affordability", "heat", step=10.0)
    prop_type = st.selectbox("Property Type", ["House / Freehold", "Condo / Townhome"], 
                             index=0 if aff.get('prop_type') == "House / Freehold" else 1,
                             key="affordability:prop_type", on_change=sync_widget, args=("affordability:prop_type",))
    strata = cloud_input("Monthly Strata", "affordability", "strata", step=10.0) if prop_type == "Condo / Townhome" else 0

st.divider()

# --- 7. INCOME & DEBT (THE SMART SYNC) ---
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

with col_3:
    st.info("**💡 Underwriting Insights:** T4 uses 100%, Additional uses 2-yr average, Rental haircut to 80%.")

# --- 8. CALCULATION LOGIC ---
monthly_inc = total_qualifying / 12
gds_max = (monthly_inc * 0.39) - f_heat - (f_ptax/12) - (strata*0.5)
tds_max = (monthly_inc * 0.44) - f_heat - (f_ptax/12) - (strata*0.5) - i_debt
max_pi_stress = min(gds_max, tds_max)

if max_pi_stress > 0:
    r_mo_stress = (s_rate/100)/12
    # Zero Division Check
    if r_mo_stress > 0:
        raw_loan = max_pi_stress * (1 - (1+r_mo_stress)**-300) / r_mo_stress
    else:
        raw_loan = max_pi_stress * 300
    
    loan_amt = custom_round_up(raw_loan)
    r_mo_contract = (c_rate/100)/12
    
    # Zero Division Check
    if r_mo_contract > 0:
        contract_pi = (loan_amt * r_mo_contract) / (1 - (1+r_mo_contract)**-300)
    else:
        contract_pi = loan_amt / 300
    
    max_purchase = loan_amt + f_dp
    st.session_state.aff_final = {'max_purchase': max_purchase, 'down_payment': f_dp}
    
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max Purchase", f"${max_purchase:,.0f}")
    m2.metric("Max Loan", f"${loan_amt:,.0f}")
    m3.metric("Monthly P&I", f"${contract_pi:,.0f}")
    m4.metric("Stress P&I", f"${max_pi_stress:,.0f}")
