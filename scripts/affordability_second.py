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

# --- 1. THEME & STYLING ---
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
p1_name = prof.get('p1_name', 'Dori')
p2_name = prof.get('p2_name', 'Kevin')

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

# Default values for new scenarios
if aff_sec.get('target_price', 0) == 0:
    scraped_yield = intel.get("provincial_yields", {}).get(current_res_prov, 3.8)
    tax_rate_lookup = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
    def_tax = tax_rate_lookup.get(current_res_prov, 0.0075)
    
    aff_sec.update({
        "down_payment": 200000.0, "target_price": 600000.0,
        "manual_rent": (600000.0 * (scraped_yield/100)) / 12,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "strata_mo": 400.0, "insurance_mo": 100.0, "vacancy_months": 1.0,
        "rm_mo": 150.0, "mgmt_pct": 5.0, "annual_prop_tax": 600000.0 * def_tax,
        "asset_province": current_res_prov, "use_case": "Rental Property", "is_vanc": False
    })
    if st.session_state.get("is_logged_in"):
        supabase.table("user_vault").upsert({"id": st.session_state.username, "data": st.session_state.app_db}).execute()

# --- 4. TITLE & STORYBOX ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Strategic Brief: Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} and {p2_name}</b> are evaluating the next step. 
        Whether deploying into a <b>self-sustaining rental asset</b> or a <b>vacation home</b>, 
        this map determines viability within your household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. TOP LEVEL SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    def_p_idx = prov_options.index(aff_sec.get('asset_province', current_res_prov)) if aff_sec.get('asset_province') in prov_options else 0
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, index=def_p_idx, 
                                  key="affordability_second:asset_province", on_change=sync_widget, args=("affordability_second:asset_province",))
with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"],
                             index=0 if aff_sec.get('use_case') == "Rental Property" else 1,
                             key="affordability_second:use_case", on_change=sync_widget, args=("affordability_second:use_case",))
    is_rental = True if use_case == "Rental Property" else False

scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)

# --- 6. CORE CALCULATION PREP ---
def get_float(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

p1_annual = get_float('p1_t4') + get_float('p1_bonus') + get_float('p1_commission')
p2_annual = get_float('p2_t4') + get_float('p2_bonus') + get_float('p2_commission')
m_inc = (p1_annual + p2_annual + (get_float('inv_rental_income', 0) * 0.80)) / 12

m_bal = get_float('m_bal')
m_rate_p = (get_float('m_rate', 4.0) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (get_float('prop_taxes', 4200) / 12) + get_float('heat_pmt', 125)
p_debts = get_float('car_loan') + get_float('student_loan') + get_float('cc_pmt') + (get_float('loc_balance') * 0.03)

# --- 7. CORE INPUTS (SYNCED) ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000.0)

    # Max Buying Power Logic
    stress_rate = max(5.25, aff_sec.get('contract_rate', 4.26) + 2.0)
    r_stress = (stress_rate / 100) / 12
    stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)
    rent_offset = (aff_sec.get('manual_rent', 0) * 0.80) if is_rental else 0
    
    qual_room = (m_inc * 0.44) + rent_offset - primary_mtg - primary_carrying - p_debts - (aff_sec.get('annual_prop_tax', 0) / 12)
    max_by_income = (qual_room / stress_k) + f_dp if qual_room > 0 else f_dp
    max_by_dp = f_dp / 0.20
    
    if max_by_income < max_by_dp:
        max_buying_power = custom_round_up(max_by_income)
        limit_reason = "Income Test"
    else:
        max_buying_power = custom_round_up(max_by_dp)
        limit_reason = "20% Down Payment rule"

    st.markdown(f"""
        <div style="background-color: #E9ECEF; padding: 12px; border-radius: 8px; border: 1px solid #DEE2E6; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 0.8em; color: {SLATE_ACCENT}; font-weight: bold;">Max Qualified Buying Power</p>
            <p style="margin: 0; font-size: 1.4em; color: {SLATE_ACCENT}; font-weight: 800;">${max_buying_power:,.0f}</p>
            <p style="margin: 0; font-size: 0.75em; color: #6C757D; line-height: 1.2;">Note: Max power limited by <b>{limit_reason}</b>.</p>
        </div>
    """, unsafe_allow_html=True)

    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000.0, max_value=max_buying_power)
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent")
        st.caption(f"💡 {asset_province} Yield Guide: {scraped_yield}%")
        f_vacancy = cloud_input("Vacancy (no. of months)", "affordability_second", "vacancy_months", min_value=0.0, max_value=12.0)
    else:
        st.info(f"ℹ️ Secondary Home: Household income must support costs in {asset_province}.")

with c_right:
    st.subheader("🏙️ Carrying Costs")
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100.0)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10.0)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10.0)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10.0)
    
    bc_extra_mo = 0
    if asset_province == "BC" and not is_rental:
        st.markdown("---")
        spec_tax = f_price * 0.005
        vanc_check = st.checkbox("Property in Vancouver?", value=aff_sec.get('is_vanc', False),
                                 key="affordability_second:is_vanc", on_change=sync_widget, args=("affordability_second:is_vanc",))
        vanc_empty_tax = f_price * 0.03 if vanc_check else 0
        st.warning(f"🌲 BC Specifics: Spec Tax: ${spec_tax:,.0f} | Empty Home Tax: ${vanc_empty_tax:,.0f}")
        bc_extra_mo = (spec_tax + vanc_empty_tax) / 12

    if is_rental:
        mgmt_pct = st.slider("Property Management Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0)),
                            key="affordability_second:mgmt_pct", on_change=sync_widget, args=("affordability_second:mgmt_pct",))
        mgmt_fee = (f_rent * (mgmt_pct / 100))
    else:
        mgmt_fee = 0
    
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + bc_extra_mo + mgmt_fee
    st.markdown(f"""<div style="background-color: #E9ECEF; color: {SLATE_ACCENT}; padding: 8px 15px; border-radius: 5px; border: 1px solid #DEE2E6; text-align: center; margin-top: 10px;">
        Total Monthly OpEx: <b>${total_opex_mo:,.0f}</b></div>""", unsafe_allow_html=True)

# --- 8. ANALYSIS & TABLES ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (f_rent * (12 - f_vacancy)) / 12 if is_rental else 0
asset_net = realized_rent - total_opex_mo - new_p_i

net_h_inc = (p1_annual + p2_annual + get_float('inv_rental_income')) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo)
safety_margin = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0

st.subheader("📝 Monthly Cash Flow Breakdown")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([
        {"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"},
        {"Item": "Primary Home & Debts", "Amount": f"-${primary_mtg + primary_carrying + p_debts:,.0f}"},
        {"Item": "Monthly Surplus", "Amount": f"${net_h_inc - (primary_mtg + primary_carrying + p_debts):,.0f}"}
    ]))
with c2:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([
        {"Item": "Realized Rent", "Amount": f"${realized_rent:,.0f}"},
        {"Item": "OpEx & New Mortgage", "Amount": f"-${total_opex_mo + new_p_i:,.0f}"},
        {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}
    ]))

# --- 9. METRICS BAR ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
with m1:
    m_color = DARK_GREEN if asset_net >= 0 else CRIMSON_RED
    st.markdown(f"<b style='font-size: 0.85em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{m_color}; margin-top: 0;'>${asset_net:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)
with m2:
    coc = (asset_net * 12 / f_dp * 100) if f_dp > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Cash-on-Cash Return</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{coc:.1f}%</h3>", unsafe_allow_html=True)
with m3:
    st.markdown(f"<b style='font-size: 0.85em;'>Household Safety Margin</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{'#16a34a' if safety_margin > 10 else '#ca8a04'}; margin-top: 0;'>{safety_margin:.1f}%</h3>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<b style='font-size: 0.85em;'>Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}</h3>", unsafe_allow_html=True)

# --- 10. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict")
is_neg_carry = is_rental and asset_net < 0
is_low_safety = not is_rental and safety_margin < 45
is_unsustainable = overall_cash_flow < 0

if is_unsustainable:
    v_status, v_color, v_bg = "❌ Unsustainable Move", "#dc2626", "#FEF2F2"
    v_msg = "Total monthly obligations exceed your current net income inflow."
elif is_neg_carry or is_low_safety:
    v_status, v_color, v_bg = "⚠️ Speculative Move", "#ca8a04", "#FFFBEB"
    v_msg = "Acquisition is viable on paper but carries significant lifestyle opportunity costs."
else:
    v_status, v_color, v_bg = "✅ Strategically Sound", "#16a34a", "#F0FDF4"
    v_msg = "Your household ecosystem shows strong resilience for this acquisition."

st.markdown(f"""
<div style='background-color: {v_bg}; padding: 20px; border-radius: 10px; border: 1.5px solid {v_color}; color: {SLATE_ACCENT};'>
    <h4 style='color: {v_color}; margin-top: 0;'>{v_status}</h4>
    <p style='font-size: 1.05em; margin-bottom: 10px;'>{v_msg}</p>
    <div style='font-size: 1em;'>
        <p>• <b>The "Blind Spot" Warning:</b> The overall cash flow of <b>${overall_cash_flow:,.0f}</b> does not account for lifestyle expenses (food, shopping, etc).</p>
        {'<p>• <b>Negative Carry:</b> This rental requires <b>${:,.0f}</b>/mo from your salary to stay afloat. It is a growth play, not cash flow.</p>'.format(abs(asset_net)) if is_neg_carry else ''}
        {'<p>• <b>Leverage Alert:</b> Your Safety Margin is <b>{:.1f}%</b>. Below 45% is considered high-leverage for secondary homes.</p>'.format(safety_margin) if is_low_safety else ''}
    </div>
</div>
""", unsafe_allow_html=True)

show_disclaimer()
