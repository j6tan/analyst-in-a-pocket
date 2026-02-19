import streamlit as st
import pandas as pd
import os
import json
import math
import time
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, load_user_data, init_session_state, supabase

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. THEME & UTILS ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def custom_round_up(n):
    if n <= 0: return 0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return int(math.ceil(n / step) * step)

def get_marginal_tax_rate(income):
    if income <= 55867: return 20.06
    elif income <= 111733: return 31.00
    elif income <= 173205: return 40.70
    elif income <= 246752: return 45.80
    else: return 53.50

# --- 3. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

if 'affordability_second' not in st.session_state.app_db:
    st.session_state.app_db['affordability_second'] = {}
aff_sec = st.session_state.app_db['affordability_second']

# --- 4. HEADER ---
st.title("The Portfolio Expansion Map")

# --- 5. SELECTORS & INCOME CONTEXT ---
p1_inc = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
p2_inc = float(prof.get('p2_t4', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))
rental_income_existing = float(prof.get('inv_rental_income', 0))
m_inc = (p1_inc + p2_inc + (rental_income_existing * 0.80)) / 12

m_bal = float(prof.get('m_bal', 0))
m_rate_p = (float(prof.get('m_rate', 4.0)) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (float(prof.get('prop_taxes', 0)) / 12) + float(prof.get('heat_pmt', 0))
p_debts = float(prof.get('car_loan', 0)) + float(prof.get('student_loan', 0)) + float(prof.get('cc_pmt', 0)) + (float(prof.get('loc_balance', 0)) * 0.03)

# --- 6. INPUTS ---
c_left, c_right = st.columns(2)
with c_left:
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000)
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000)
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent", step=100)
    f_vacancy = cloud_input("Vacancy (Months/Year)", "affordability_second", "vacancy_months", step=0.5)

with c_right:
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10)
    
    t1, t2 = get_marginal_tax_rate(p1_inc), get_marginal_tax_rate(p2_inc)
    tax_map = {f"{p1_name} ({t1}%)": t1, f"{p2_name} ({t2}%)": t2}
    tax_owner = st.radio("Registered Owner", list(tax_map.keys()), horizontal=True, key="aff_sec_tax_owner_radio")
    marginal_tax_rate = tax_map[tax_owner]

# --- 7. CALCULATIONS ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12
taxable_asset_income = (realized_rent * 12) - (f_tax + (f_ins * 12) + (f_strata * 12) + (f_rm * 12))
asset_tax_mo = max(0, (taxable_asset_income * (marginal_tax_rate / 100)) / 12)

total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm
asset_net = realized_rent - total_opex_mo - new_p_i - asset_tax_mo
net_h_inc = (p1_inc + p2_inc) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo + asset_tax_mo)
safety_margin = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0

# --- 8. RESULTS DASHBOARD ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Asset Net Cash", f"${asset_net:,.0f}/mo")
m2.metric("Cash-on-Cash", f"{(asset_net * 12 / f_dp * 100) if f_dp > 0 else 0:.1f}%")

# Clarity Improvement: Explicit Tooltips for safety metrics
m3.metric("Safety Margin %", f"{safety_margin:.1f}%", help="Percentage of total income remaining after ALL debt and property costs are paid, but BEFORE lifestyle spending.")
m4.metric("Overall Surplus", f"${overall_cash_flow:,.0f}", help="Total monthly cash remaining after primary home costs, existing debts, and the new property costs.")

# --- 9. STRATEGIC VERDICT (The Detailed Clarity Section) ---
st.subheader("🎯 Strategic Verdict")

b_data = st.session_state.app_db.get('budget', {})
lifestyle_spend = sum([float(b_data.get(k, 0)) for k in ['groceries', 'dining', 'childcare', 'pets', 'gas_transit', 'car_ins_maint', 'utilities', 'shopping', 'entertainment', 'health', 'misc']])
true_net = overall_cash_flow - lifestyle_spend
household_expense_ratio = ((primary_mtg + primary_carrying + p_debts + lifestyle_spend + new_p_i + total_opex_mo + asset_tax_mo) / (net_h_inc + realized_rent)) * 100

# Color Logic
ratio_text_color = "#dc2626" if household_expense_ratio > 80 else "#16a34a"

st.markdown(f"""
<div style='background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 1px solid #DEE2E6; color: #2E2B28;'>
    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 30px;'>
        <div>
            <p style='margin: 0; font-size: 0.85em; color: #666; font-weight: bold;'>TRUE NET POSITION</p>
            <p style='margin: 0; font-size: 1.8em; font-weight: bold; color: {'#dc2626' if true_net < 0 else '#16a34a'};'>${true_net:,.0f}<small>/mo</small></p>
            <p style='margin: 10px 0; font-size: 0.85em; line-height: 1.4; color: #4A4E5A;'>
                This is your <b>actual walk-away surplus</b>. It accounts for your primary home, existing debts, the new rental's negative/positive carry, and your full <b>Monthly Lifestyle Budget</b>.
            </p>
        </div>
        <div>
            <p style='margin: 0; font-size: 0.85em; color: #666; font-weight: bold;'>TOTAL EXPENSE RATIO</p>
            <p style='margin: 0; font-size: 1.8em; font-weight: bold; color: {ratio_text_color};'>{household_expense_ratio:.1f}%</p>
            <p style='margin: 10px 0; font-size: 0.85em; line-height: 1.4; color: #4A4E5A;'>
                This measures what % of your total income is consumed by obligations. 
                <br><span style='color: {ratio_text_color}; font-weight: bold;'>Status: { "High Risk (>80%)" if household_expense_ratio > 80 else "Healthy (<80%)"}</span>
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)



# --- 10. STRESS TEST ---
st.write("")
col_s1, col_s2 = st.columns(2)
with col_s1:
    st.markdown("### 🛡️ Resilience Check")
    job_loss_months = (f_dp / (lifestyle_spend + primary_mtg + primary_carrying + new_p_i + total_opex_mo)) if f_dp > 0 else 0
    st.info(f"**Emergency Buffer:** If income stops, your current down payment capital could float all household and property costs for **{job_loss_months:.1f} months**.")
with col_s2:
    rate_shock = (target_loan * 0.02 / 12)
    st.warning(f"**Rate Shock:** A +2% increase in mortgage rates would reduce your monthly surplus by **${rate_shock:,.0f}**.")

show_disclaimer()
