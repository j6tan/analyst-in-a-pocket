import streamlit as st
import pandas as pd
import os
import json
import math
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase, load_user_data, init_session_state

# --- UNIVERSAL LOADER ---
init_session_state()
if not st.session_state.app_db.get('profile') and st.session_state.get('username'):
    with st.spinner("🔄 Hydrating Data..."):
        load_user_data(st.session_state.username)
        st.rerun()

inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

def custom_round_up(n):
    if n <= 0: return 0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return int(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Primary Client')
p2_name = prof.get('p2_name', '')

if 'affordability_second' not in st.session_state.app_db:
    st.session_state.app_db['affordability_second'] = {}
aff_sec = st.session_state.app_db['affordability_second']

if aff_sec.get('target_price', 0) == 0:
    aff_sec.update({"down_payment": 200000, "target_price": 600000, "contract_rate": 4.26, "manual_rent": 2500, "vacancy_months": 1.0, "annual_prop_tax": 3000, "strata_mo": 400, "insurance_mo": 100, "rm_mo": 150, "asset_province": current_res_prov, "use_case": "Rental Property", "mgmt_pct": 5.0, "is_vanc": False})

header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} {f'and {p2_name}' if p2_name else ''}</b>: Investment viability analysis.
    </p>
</div>
""", unsafe_allow_html=True)

ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, index=prov_options.index(aff_sec.get('asset_province', current_res_prov)), key="affordability_second:asset_province", on_change=sync_widget, args=("affordability_second:asset_province",))
with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"], index=0 if aff_sec.get('use_case') == "Rental Property" else 1, key="affordability_second:use_case", on_change=sync_widget, args=("affordability_second:use_case",))
    is_rental = True if use_case == "Rental Property" else False

def get_f(k, d=0):
    try: return float(prof.get(k, d))
    except: return float(d)

m_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + (get_f('inv_rental_income') * 0.80)) / 12
m_bal = get_f('m_bal')
m_rate_p = (get_f('m_rate', 4.0) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (get_f('prop_taxes', 4200) / 12) + get_f('heat_pmt', 125)
p_debts = get_f('car_loan') + get_f('student_loan') + get_f('cc_pmt') + (get_f('loc_balance') * 0.03)

st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    # INTEGERS
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000)
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000)

    calc_rate = float(aff_sec.get('contract_rate', 4.26))
    calc_rent = float(aff_sec.get('manual_rent', 0.0))
    stress_rate = max(5.25, calc_rate + 2.0)
    r_stress = (stress_rate / 100) / 12
    stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)
    
    rent_offset = (calc_rent * 0.80) if is_rental else 0
    qual_room = (m_inc * 0.44) + rent_offset - primary_mtg - primary_carrying - p_debts - (float(aff_sec.get('annual_prop_tax', 0)) / 12)
    
    max_by_income = (qual_room / stress_k) + f_dp if qual_room > 0 else f_dp
    max_by_dp = f_dp / 0.20
    max_buying_power = custom_round_up(min(max_by_income, max_by_dp))

    st.markdown(f"""
        <div style="background-color: #E9ECEF; padding: 12px; border-radius: 8px; border: 1px solid #DEE2E6; margin-top: 10px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 0.8em; color: {SLATE_ACCENT}; font-weight: bold;">Max Qualified Buying Power</p>
            <p style="margin: 0; font-size: 1.4em; color: {SLATE_ACCENT}; font-weight: 800;">${max_buying_power:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

    # FLOAT (Rate)
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    # INTEGERS (Rent, Vacancy is exception but keep as float if needed, typically int months)
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent", step=50)
        f_vacancy = cloud_input("Vacancy (no. of months)", "affordability_second", "vacancy_months", min_value=0.0, max_value=12.0, step=0.5) # Float allowed here
    else: f_rent, f_vacancy = 0, 0

with c_right:
    st.subheader("🏙️ Carrying Costs")
    # INTEGERS
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10)
    bc_extra = 0
    if asset_province == "BC" and not is_rental:
        st.markdown("---")
        vanc_check = st.checkbox("Property in Vancouver?", value=aff_sec.get('is_vanc', False), key="affordability_second:is_vanc", on_change=sync_widget, args=("affordability_second:is_vanc",))
        bc_extra = ((f_price * 0.005) + (f_price * 0.03 if vanc_check else 0)) / 12

    mgmt_fee = (f_rent * (st.slider("Mgmt Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0)), key="affordability_second:mgmt_pct", on_change=sync_widget, args=("affordability_second:mgmt_pct",)) / 100)) if is_rental else 0
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + bc_extra + mgmt_fee

# --- 9. ANALYSIS ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12 if is_rental else 0
asset_net = realized_rent - total_opex_mo - new_p_i
net_h_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + get_f('inv_rental_income')) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo)

st.subheader("📝 Monthly Cash Flow Breakdown")
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([{"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"}, {"Item": "Primary Home & Debts", "Amount": f"-${primary_mtg + primary_carrying + p_debts:,.0f}"}, {"Item": "Monthly Surplus", "Amount": f"${net_h_inc - (primary_mtg + primary_carrying + p_debts):,.0f}"}]))
with col_b2:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([{"Item": "Realized Rent", "Amount": f"${realized_rent:,.0f}"}, {"Item": "OpEx & New Mortgage", "Amount": f"-${total_opex_mo + new_p_i:,.0f}"}, {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}]))

show_disclaimer()
