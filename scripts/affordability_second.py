import streamlit as st
import pandas as pd
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
CRIMSON_RED = "#A52A2A"
DARK_GREEN = "#1B4D3E"

def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    step = {1:10, 2:10, 3:10, 4:100, 5:100, 6:1000, 7:10000}.get(digits, 50000)
    return float(math.ceil(n / step) * step)

# --- 2. DATA RETRIEVAL ---
prof = st.session_state.app_db.get('profile', {})
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Primary Client')
p2_name = prof.get('p2_name', '')

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()

# --- 3. PERSISTENCE & INITIALIZATION ---
if 'affordability_second' not in st.session_state.app_db:
    st.session_state.app_db['affordability_second'] = {}
aff_sec = st.session_state.app_db['affordability_second']

# --- 4. TITLE & STORYBOX ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Strategic Brief: Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} {f'and {p2_name}' if p2_name else ''}</b> are evaluating the next step in wealth expansion. 
        We are testing the viability of a secondary asset within your household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. TOP LEVEL SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, 
                                  index=prov_options.index(aff_sec.get('asset_province', current_res_prov)), 
                                  key="affordability_second:asset_province", on_change=sync_widget, args=("affordability_second:asset_province",))
with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"],
                             index=0 if aff_sec.get('use_case') == "Rental Property" else 1,
                             key="affordability_second:use_case", on_change=sync_widget, args=("affordability_second:use_case",))
    is_rental = True if use_case == "Rental Property" else False

# --- 6. LIVE CALCULATION FOR MAX BUYING POWER ---
def get_f(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

# Household Income & Primary Obligations
m_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + (get_f('inv_rental_income') * 0.80)) / 12
m_rate_p = (get_f('m_rate', 4.0) / 100) / 12
primary_mtg = (get_f('m_bal') * m_rate_p) / (1 - (1 + m_rate_p)**-300) if get_f('m_bal') > 0 else 0
primary_carrying = (get_f('prop_taxes', 4200) / 12) + get_f('heat_pmt', 125)
p_debts = get_f('car_loan') + get_f('student_loan') + get_f('cc_pmt') + (get_f('loc_balance') * 0.03)

# Inputs that affect Max Power
f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000.0)
c_rate = aff_sec.get('contract_rate', 4.26)
s_rate = max(5.25, c_rate + 2.0)
r_stress = (s_rate / 100) / 12
stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)

# The "Price-Lower-Of" Logic
qual_room = (m_inc * 0.44) - primary_mtg - primary_carrying - p_debts 
# (Simple approximation: we assume a small tax/heat buffer for the new property in the qual test)
max_by_income = ((qual_room - 250) / stress_k) + f_dp if qual_room > 250 else f_dp
max_by_dp = f_dp / 0.20

max_buying_power = custom_round_up(min(max_by_income, max_by_dp))
limit_reason = "Income (GDS/TDS)" if max_by_income < max_by_dp else "20% Down Payment Rule"

st.markdown(f"""
    <div style="background-color: #E9ECEF; padding: 12px; border-radius: 8px; border: 1px solid #DEE2E6; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 0.8em; color: {SLATE_ACCENT}; font-weight: bold;">Max Qualified Buying Power</p>
        <p style="margin: 0; font-size: 1.4em; color: {SLATE_ACCENT}; font-weight: 800;">${max_buying_power:,.0f}</p>
        <p style="margin: 0; font-size: 0.75em; color: #6C757D;">Limited by: <b>{limit_reason}</b></p>
    </div>
""", unsafe_allow_html=True)

# --- 7. DYNAMIC INPUTS ---
c_left, c_right = st.columns(2)
with c_left:
    st.subheader("💰 Asset Selection")
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000.0, max_value=max_buying_power)
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    
    # PRICE-LINKED RENT DEFAULTS
    scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)
    suggested_rent = (f_price * (scraped_yield/100)) / 12
    if aff_sec.get('manual_rent', 0) == 0: aff_sec['manual_rent'] = suggested_rent
    
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent")
        st.caption(f"💡 {asset_province} Average Yield: {scraped_yield}% (est. ${suggested_rent:,.0f}/mo)")
        f_vacancy = cloud_input("Vacancy (no. of months)", "affordability_second", "vacancy_months", min_value=0.0, max_value=12.0)
    else:
        f_rent, f_vacancy = 0, 0

with c_right:
    st.subheader("🏙️ Carrying Costs")
    # PRICE-LINKED TAX/MAINT DEFAULTS
    tax_rate = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}.get(asset_province, 0.0075)
    if aff_sec.get('annual_prop_tax', 0) == 0: aff_sec['annual_prop_tax'] = f_price * tax_rate
    
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100.0)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10.0)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10.0)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10.0)
    
    bc_extra = 0
    if asset_province == "BC" and not is_rental:
        vanc_check = st.checkbox("In Vancouver City Limits?", value=aff_sec.get('is_vanc', False), key="affordability_second:is_vanc", on_change=sync_widget, args=("affordability_second:is_vanc",))
        bc_extra = ((f_price * 0.005) + (f_price * 0.03 if vanc_check else 0)) / 12

    mgmt_fee = (f_rent * (st.slider("Mgmt Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0)), key="affordability_second:mgmt_pct", on_change=sync_widget, args=("affordability_second:mgmt_pct",)) / 100)) if is_rental else 0
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + bc_extra + mgmt_fee

# --- 8. ANALYSIS & METRICS ---
target_loan = max(0, f_price - f_dp)
r_c = (f_rate / 100) / 12
new_p_i = (target_loan * r_c) / (1 - (1 + r_c)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12
asset_net = realized_rent - total_opex_mo - new_p_i
net_h_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + get_f('inv_rental_income')) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo)
safety_margin = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0

st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Asset Net Cash", f"${asset_net:,.0f}/mo", delta=None, delta_color="normal")
m2.metric("Cash-on-Cash", f"{(asset_net*12/f_dp*100) if f_dp > 0 else 0:.1f}%")
m3.metric("Household Safety", f"{safety_margin:.1f}%")
m4.metric("Overall Surplus", f"${overall_cash_flow:,.0f}")

# --- 9. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict")
is_neg = is_rental and asset_net < 0
is_unsustainable = overall_cash_flow < 0

if is_unsustainable:
    v_status, v_color, v_bg = "❌ Unsustainable", "#dc2626", "#FEF2F2"
    v_msg = "Current household income cannot support the total debt load of both properties."
elif is_neg:
    v_status, v_color, v_bg = "⚠️ Speculative (Negative Carry)", "#ca8a04", "#FFFBEB"
    v_msg = "The asset requires monthly salary support. Viable only for long-term appreciation."
else:
    v_status, v_color, v_bg = "✅ Strategically Sound", "#16a34a", "#F0FDF4"
    v_msg = "The acquisition fits comfortably within your current financial ecosystem."

st.markdown(f"""
<div style='background-color: {v_bg}; padding: 20px; border-radius: 10px; border: 1.5px solid {v_color}; color: {SLATE_ACCENT};'>
    <h4 style='color: {v_color}; margin-top: 0;'>{v_status}</h4>
    <p style='margin-bottom: 10px;'>{v_msg}</p>
    <div style='font-size: 0.95em;'>
        <p>• <b>Total Surplus:</b> You are left with <b>${overall_cash_flow:,.0f}</b> per month for all other lifestyle expenses.</p>
        {'<p>• <b>Note:</b> Lenders may require additional cash reserves for a secondary residence.</p>' if not is_rental else ''}
    </div>
</div>
""", unsafe_allow_html=True)

show_disclaimer()
