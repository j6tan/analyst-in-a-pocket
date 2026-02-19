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
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

if 'affordability_second' not in st.session_state.app_db:
    st.session_state.app_db['affordability_second'] = {}
aff_sec = st.session_state.app_db['affordability_second']

# Default initialization
if not aff_sec.get('initialized'):
    aff_sec.update({
        "down_payment": 200000, "target_price": 600000, "contract_rate": 4.5, 
        "manual_rent": 2500, "vacancy_months": 1.0, "annual_prop_tax": 3000, 
        "strata_mo": 400, "insurance_mo": 100, "rm_mo": 150, 
        "asset_province": current_res_prov, "use_case": "Rental Property", 
        "mgmt_pct": 5.0, "initialized": True
    })

# --- 4. HEADER ---
st.title("The Portfolio Expansion Map")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Strategic Brief: Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} {'and ' + p2_name if p2_name else ''}</b> are evaluating the next step. 
        Determine viability within your household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "NB"]
    asset_province = st.selectbox("Asset Location", prov_options, index=prov_options.index(aff_sec.get('asset_province', 'BC')), key="aff_sec_prov_widget")
    aff_sec['asset_province'] = asset_province
with ts_col2:
    use_case = st.selectbox("Use Case", ["Rental Property", "Family Vacation Home"], index=0 if aff_sec.get('use_case') == "Rental Property" else 1, key="aff_sec_use_widget")
    aff_sec['use_case'] = use_case
    is_rental = (use_case == "Rental Property")

# --- 6. INCOME & DEBT CONTEXT ---
p1_inc = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
p2_inc = float(prof.get('p2_t4', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))
total_income = p1_inc + p2_inc + (float(prof.get('inv_rental_income', 0)) * 0.8)
m_inc = total_income / 12

m_bal = float(prof.get('m_bal', 0))
m_rate_p = (float(prof.get('m_rate', 4.0)) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (float(prof.get('prop_taxes', 0)) / 12) + float(prof.get('heat_pmt', 0))
p_debts = float(prof.get('car_loan', 0)) + float(prof.get('student_loan', 0)) + float(prof.get('cc_pmt', 0)) + (float(prof.get('loc_balance', 0)) * 0.03)

# --- 7. INPUTS ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000)
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000)
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent", step=100)
        f_vacancy = cloud_input("Vacancy (Months/Year)", "affordability_second", "vacancy_months", step=0.5)
    else:
        f_rent, f_vacancy = 0, 0

with c_right:
    st.subheader("🏙️ Carrying Costs")
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10)
    
    st.markdown("**Whose tax bracket applies to this asset?**")
    t1, t2 = get_marginal_tax_rate(p1_inc), get_marginal_tax_rate(p2_inc)
    tax_options = {f"{p1_name} ({t1}%)": t1, f"{p2_name} ({t2}%)": t2}
    tax_rate_input = tax_options[st.radio("Select Owner", list(tax_options.keys()), horizontal=True, key="aff_sec_tax_radio")]

    mgmt_fee = (f_rent * (st.slider("Mgmt Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0))) / 100)) if is_rental else 0
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + mgmt_fee

# --- 8. CALCULATIONS ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12 if is_rental else 0

# Tax on Rental Income
taxable_income = (realized_rent * 12) - (f_tax + (f_ins * 12) + (f_strata * 12) + (f_rm * 12))
re_tax_mo = max(0, (taxable_income * (tax_rate_input / 100)) / 12) if is_rental else 0

asset_net = realized_rent - total_opex_mo - new_p_i - re_tax_mo
net_h_inc = (p1_inc + p2_inc) * 0.75 / 12 # Estimated take-home
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo + re_tax_mo)

st.subheader("📝 Monthly Cash Flow Breakdown")
cb1, cb2 = st.columns(2)
with cb1:
    st.table(pd.DataFrame([{"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"}, {"Item": "Primary Home & Debts", "Amount": f"-${primary_mtg + primary_carrying + p_debts:,.0f}"}]))
with cb2:
    st.table(pd.DataFrame([{"Item": "Asset Net Rent", "Amount": f"${realized_rent:,.0f}"}, {"Item": "Asset Costs & Mtg", "Amount": f"-${total_opex_mo + new_p_i + re_tax_mo:,.0f}"}]))

st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Asset Net Cash", f"${asset_net:,.0f}/mo")
m2.metric("Cash-on-Cash", f"{(asset_net * 12 / f_dp * 100) if f_dp > 0 else 0:.1f}%")
m3.metric("Safety Margin", f"{(overall_cash_flow / (net_h_inc + realized_rent) * 100):.1f}%")
m4.metric("Overall Surplus", f"${overall_cash_flow:,.0f}")

# --- 9. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict")
b_data = st.session_state.app_db.get('budget', {})
lifestyle_spend = sum([float(b_data.get(k, 0)) for k in ['groceries', 'dining', 'childcare', 'pets', 'gas_transit', 'car_ins_maint', 'utilities', 'shopping', 'entertainment', 'health', 'misc']])
true_net = overall_cash_flow - lifestyle_spend
expense_ratio = ((primary_mtg + primary_carrying + p_debts + lifestyle_spend + new_p_i + total_opex_mo) / (net_h_inc + realized_rent)) * 100

if overall_cash_flow < 0:
    v_status, v_color, v_bg = "❌ Critical Risk: Overexposed", "#dc2626", "#FEF2F2"
    v_insight = "Fixed debts exceed income. Lender rejection likely."
elif true_net < 0:
    v_status, v_color, v_bg = "⚠️ Lifestyle Risk: House Poor", "#ca8a04", "#FFFBEB"
    v_insight = f"Must cut ${abs(true_net):,.0f}/mo from spending to avoid deficit."
elif is_rental and asset_net < 0:
    v_status, v_color, v_bg = "🟡 Strategic Play: Negative Carry", "#4A4E5A", "#F8F9FA"
    v_insight = "Asset loses cash monthly. Requires personal subsidy for equity growth."
else:
    v_status, v_color, v_bg = "✅ Wealth Accelerator", "#16a34a", "#F0FDF4"
    v_insight = "Acquisition fits comfortably within income and lifestyle targets."

st.markdown(f"""
<div style='background-color: {v_bg}; padding: 25px; border-radius: 12px; border: 2px solid {v_color};'>
    <h4 style='color: {v_color}; margin-top: 0;'>{v_status}</h4>
    <p style='font-weight: 500;'>{v_insight}</p>
    <div style='display: flex; gap: 40px; margin-top: 15px;'>
        <div><small>TRUE NET POSITION</small><br><b>${true_net:,.0f}/mo</b></div>
        <div><small>TOTAL EXPENSE RATIO</small><br><b>{expense_ratio:.1f}%</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 10. STRESS TEST ---
st.write("")
col_s1, col_s2 = st.columns(2)
with col_s1:
    st.markdown("### 🛡️ Stress Test")
    job_loss = (f_dp / (lifestyle_spend + primary_mtg + primary_carrying + new_p_i + total_opex_mo)) if f_dp > 0 else 0
    st.write(f"**Liquidity:** Capital floats all costs for **{job_loss:.1f} months** if income hits zero.")
with col_s2:
    rate_shock = (target_loan * 0.02 / 12)
    st.write(f"**Rate Shock:** A +2% rate spike reduces monthly net by **${rate_shock:,.0f}**.")

show_disclaimer()
