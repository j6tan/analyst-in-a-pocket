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

# Color constants for metrics
CRIMSON_RED = "#A52A2A"
DARK_GREEN = "#1B4D3E"

# --- ROUNDING UTILITY ---
def custom_round_up(n):
    if n <= 0: return 0.0
    digits = int(math.log10(n)) + 1
    if digits <= 3: step = 10
    elif digits <= 5: step = 100
    elif digits == 6: step = 1000
    elif digits == 7: step = 10000
    else: step = 50000 
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

# --- INITIALIZE DEFAULTS (Prevent 0.0 startup) ---
if aff_sec.get('target_price', 0) == 0:
    scraped_yield = intel.get("provincial_yields", {}).get(current_res_prov, 3.8)
    def_price = 600000.0
    def_rent = (def_price * (scraped_yield/100)) / 12
    def_tax_rate = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}.get(current_res_prov, 0.0075)
    
    aff_sec.update({
        "down_payment": 200000.0,
        "target_price": def_price,
        "contract_rate": 4.26,
        "manual_rent": def_rent,
        "vacancy_months": 1.0,
        "annual_prop_tax": def_price * def_tax_rate,
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "rm_mo": 150.0,
        "asset_province": current_res_prov,
        "use_case": "Rental Property",
        "mgmt_pct": 5.0,
        "is_vanc": False
    })
    # Save defaults
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
        <b>{p1_name} {f'and {p2_name}' if p2_name else ''}</b> are evaluating the next step. 
        Whether deploying into a <b>self-sustaining rental asset</b> or a <b>vacation home</b>, 
        this map determines viability within your household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 5. TOP LEVEL SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    curr_prov = aff_sec.get('asset_province', current_res_prov)
    if curr_prov not in prov_options: curr_prov = "BC"
    
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, 
                                  index=prov_options.index(curr_prov),
                                  key="affordability_second:asset_province",
                                  on_change=sync_widget, args=("affordability_second:asset_province",))

with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"],
                             index=0 if aff_sec.get('use_case') == "Rental Property" else 1,
                             key="affordability_second:use_case",
                             on_change=sync_widget, args=("affordability_second:use_case",))
    is_rental = True if use_case == "Rental Property" else False

# --- 6. HOUSEHOLD FINANCIALS ---
def get_f(k, d=0.0):
    try: return float(prof.get(k, d))
    except: return d

m_inc_base = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + (get_f('inv_rental_income') * 0.80)) / 12
m_bal = get_f('m_bal')
m_rate_p = (get_f('m_rate', 4.0) / 100) / 12
primary_mtg = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (get_f('prop_taxes', 4200) / 12) + get_f('heat_pmt', 125)
p_debts = get_f('car_loan') + get_f('student_loan') + get_f('cc_pmt') + (get_f('loc_balance') * 0.03)

# --- 7. CORE INPUTS & LIVE MAX POWER CALC ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    
    # 1. Down Payment
    f_dp = cloud_input("Available Down Payment ($)", "affordability_second", "down_payment", step=5000.0)
    
    # 2. Purchase Price
    f_price = cloud_input("Purchase Price ($)", "affordability_second", "target_price", step=5000.0)

    # --- INSTANT MAX POWER CALCULATION ---
    # Fetch LIVE values from session state to ensure instant reactivity
    calc_rate = float(aff_sec.get('contract_rate', 4.26))
    calc_rent = float(aff_sec.get('manual_rent', 0.0))
    calc_tax = float(aff_sec.get('annual_prop_tax', 0.0))

    # Stress Test
    stress_rate = max(5.25, calc_rate + 2.0)
    r_stress = (stress_rate / 100) / 12
    k_stress = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1) if r_stress > 0 else 1/300
    
    # Income Test (Adding 50% Rental Income to Gross, then checking 44% TDS)
    rent_addback = (calc_rent * 0.50) if is_rental else 0
    gross_income_proxy = m_inc_base + rent_addback
    max_servicing_capacity = gross_income_proxy * 0.44
    
    # Deduct obligations
    new_prop_carry_buffer = (calc_tax / 12) + 150 # Tax + Heat/Strata buffer
    available_payment = max_servicing_capacity - primary_mtg - primary_carrying - p_debts - new_prop_carry_buffer
    
    if available_payment > 0:
        max_loan_income = available_payment / k_stress
        max_price_income = max_loan_income + f_dp
    else:
        max_price_income = f_dp
        
    # Down Payment Cap (20% Rule)
    max_price_dp = f_dp / 0.20
    
    # Verdict
    max_buying_power = custom_round_up(min(max_price_income, max_price_dp))
    
    if max_price_income < max_price_dp:
        limit_reason = "Income (TDS Limit)"
    else:
        # Show the user what their income *could* support to prove rent is being counted
        limit_reason = f"20% Down Payment (Income supports ${max_price_income/1000000:.1f}M)"
    # -------------------------------

    # 3. DISPLAY MAX POWER BOX (Below Price, Above Rate)
    st.markdown(f"""
        <div style="background-color: #E9ECEF; padding: 12px; border-radius: 8px; border: 1px solid #DEE2E6; margin-top: 10px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 0.8em; color: {SLATE_ACCENT}; font-weight: bold;">Max Qualified Buying Power</p>
            <p style="margin: 0; font-size: 1.4em; color: {SLATE_ACCENT}; font-weight: 800;">${max_buying_power:,.0f}</p>
            <p style="margin: 0; font-size: 0.75em; color: #6C757D; line-height: 1.2;">Limited by: <b>{limit_reason}</b></p>
        </div>
    """, unsafe_allow_html=True)

    # 4. Rate
    f_rate = cloud_input("Mortgage Contract Rate (%)", "affordability_second", "contract_rate", step=0.1)
    
    scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)
    
    # 5. Rent
    if is_rental:
        f_rent = cloud_input("Monthly Projected Rent ($)", "affordability_second", "manual_rent")
        st.caption(f"💡 {asset_province} Yield Guide: {scraped_yield}%")
        f_vacancy = cloud_input("Vacancy (no. of months)", "affordability_second", "vacancy_months", min_value=0.0, max_value=12.0)
    else:
        f_rent, f_vacancy = 0, 0

with c_right:
    st.subheader("🏙️ Carrying Costs")
    f_tax = cloud_input("Annual Property Tax ($)", "affordability_second", "annual_prop_tax", step=100.0)
    f_strata = cloud_input("Monthly Strata ($)", "affordability_second", "strata_mo", step=10.0)
    f_ins = cloud_input("Monthly Insurance ($)", "affordability_second", "insurance_mo", step=10.0)
    f_rm = cloud_input("Repairs & Maintenance (Monthly)", "affordability_second", "rm_mo", step=10.0)
    
    bc_extra = 0
    if asset_province == "BC" and not is_rental:
        st.markdown("---")
        spec_tax = f_price * 0.005
        vanc_check = st.checkbox("Property in Vancouver?", value=aff_sec.get('is_vanc', False), key="affordability_second:is_vanc", on_change=sync_widget, args=("affordability_second:is_vanc",))
        vanc_empty_tax = f_price * 0.03 if vanc_check else 0
        st.warning(f"🌲 BC Specifics: Spec Tax: ${spec_tax:,.0f} | Empty Home Tax: ${vanc_empty_tax:,.0f}")
        bc_extra = (spec_tax + vanc_empty_tax) / 12

    mgmt_fee = (f_rent * (st.slider("Property Management Fee %", 0.0, 12.0, float(aff_sec.get('mgmt_pct', 5.0)), key="affordability_second:mgmt_pct", on_change=sync_widget, args=("affordability_second:mgmt_pct",)) / 100)) if is_rental else 0
    total_opex_mo = (f_tax / 12) + f_strata + f_ins + f_rm + bc_extra + mgmt_fee

# --- 9. ANALYSIS ---
target_loan = max(0, f_price - f_dp)
r_contract = (f_rate / 100) / 12
if r_contract > 0:
    new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) 
else:
    new_p_i = target_loan / 300 if target_loan > 0 else 0

realized_rent = (f_rent * (12 - f_vacancy)) / 12 if is_rental else 0
asset_net = realized_rent - total_opex_mo - new_p_i
net_h_inc = (get_f('p1_t4') + get_f('p1_bonus') + get_f('p2_t4') + get_f('p2_bonus') + get_f('inv_rental_income')) * 0.75 / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg + primary_carrying + p_debts + new_p_i + total_opex_mo)
safety_margin = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0

st.subheader("📝 Monthly Cash Flow Breakdown")
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([
        {"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"},
        {"Item": "Primary Home & Debts", "Amount": f"-${primary_mtg + primary_carrying + p_debts:,.0f}"},
        {"Item": "Monthly Surplus", "Amount": f"${net_h_inc - (primary_mtg + primary_carrying + p_debts):,.0f}"}
    ]))
with col_b2:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([
        {"Item": "Realized Rent", "Amount": f"${realized_rent:,.0f}"},
        {"Item": "OpEx & New Mortgage", "Amount": f"-${total_opex_mo + new_p_i:,.0f}"},
        {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}
    ]))

# --- 10. METRICS BAR ---
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

# --- 11. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict")
is_neg_carry = is_rental and asset_net < 0
is_low_safety = not is_rental and safety_margin < 45
is_unsustainable = overall_cash_flow < 0

v_html = [f"<div style='background-color: {'#FEF2F2' if is_unsustainable else '#FFFBEB' if (is_neg_carry or is_low_safety) else '#F0FDF4'}; padding: 20px; border-radius: 10px; border: 1.5px solid {'#dc2626' if is_unsustainable else '#ca8a04' if (is_neg_carry or is_low_safety) else '#16a34a'}; color: {SLATE_ACCENT};'>"]
if is_unsustainable:
    v_html.append(f"<h4 style='color: #dc2626; margin-top: 0;'>❌ Unsustainable Move</h4><p>Total monthly obligations exceed your current net income inflow.</p>")
elif is_neg_carry or is_low_safety:
    v_html.append(f"<h4 style='color: #ca8a04; margin-top: 0;'>⚠️ Speculative Move</h4><p>Acquisition is viable on paper but carries significant lifestyle opportunity costs.</p>")
else:
    v_html.append(f"<h4 style='color: #16a34a; margin-top: 0;'>✅ Strategically Sound</h4><p>Your household ecosystem shows strong resilience for this acquisition.</p>")

v_html.append("<div style='font-size: 1em;'>")
v_html.append(f"<p style='margin: 5px 0;'>• <b>The \"Blind Spot\" Warning:</b> The overall cash flow of <b>${overall_cash_flow:,.0f}</b> does not account for non-household expenses such as food, utilities, shopping, childcare, etc.</p>")
if is_neg_carry:
    v_html.append(f"<p style='margin: 5px 0;'>• <b>Negative Carry:</b> This rental requires <b>${abs(asset_net):,.0f}</b>/mo from your salary to stay afloat. This is a capital growth play, not a cash flow play.</p>")
if is_low_safety:
    v_html.append(f"<p style='margin: 5px 0;'>• <b>Leverage Alert:</b> Your Safety Margin is <b>{safety_margin:.1f}%</b>. Thresholds below 45% (pre-lifestyle) are considered high-leverage for secondary homes.</p>")
v_html.append("</div></div>")

st.markdown("".join(v_html), unsafe_allow_html=True)

show_disclaimer()
