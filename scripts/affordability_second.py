import streamlit as st
import pandas as pd
import os
import json
import math

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
prof = st.session_state.get('user_profile', {})
current_res_prov = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Dori')
p2_name = prof.get('p2_name', 'Kevin')

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()

# --- 3. TITLE & STORYTELLING BOX ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("The Portfolio Expansion Map")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Strategic Brief: Capital Deployment</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        <b>{p1_name} and {p2_name}</b> have successfully built a capital reserve and are now evaluating the next step. 
        Whether deploying this cash into a <b>self-sustaining rental asset</b> to build long-term wealth, or securing a 
        <b>vacation home</b> for family use, this map determines the viability of the move within your existing household ecosystem.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. TOP LEVEL SELECTORS ---
ts_col1, ts_col2 = st.columns(2)
with ts_col1:
    prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Saskatchewan", "Nova Scotia", "New Brunswick"]
    def_idx = prov_options.index(current_res_prov) if current_res_prov in prov_options else 0
    asset_province = st.selectbox("Asset Location (Province):", options=prov_options, index=def_idx)
with ts_col2:
    use_case = st.selectbox("Use of the Second Home:", ["Rental Property", "Family Vacation Home"])
    is_rental = True if use_case == "Rental Property" else False

scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)
tax_rate_lookup = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
default_tax_rate = tax_rate_lookup.get(asset_province, 0.0075)

# --- 5. PERSISTENCE & INITIALIZATION ---
if "aff_second_store" not in st.session_state:
    init_price = 600000.0
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "target_price": init_price,
        "manual_rent": (init_price * (scraped_yield/100)) / 12,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "vacancy_months": 1.0,
        "rm_mo": 150.0,
        "mgmt_pct": 5.0,
        "annual_prop_tax": init_price * default_tax_rate
    }
store = st.session_state.aff_second_store

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

stress_rate = max(5.25, store.get('contract_rate', 4.26) + 2.0)
r_stress = (stress_rate / 100) / 12
stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)
rent_offset = (store['manual_rent'] * 0.80) if is_rental else 0

# --- UPDATED LOGIC FOR MAX QUALIFYING PRICE ---
# Pillar 1: Debt Service Coverage (Qualifying Room)
qual_room = (m_inc * 0.44) + rent_offset - primary_mtg - primary_carrying - p_debts - (store['annual_prop_tax'] / 12)
max_by_income = (qual_room / stress_k) + store['down_payment'] if qual_room > 0 else store['down_payment']

# Pillar 2: 20% Down Payment Ceiling
max_by_dp = store['down_payment'] / 0.20

# Final result is the minimum of the two
max_buying_power = custom_round_up(min(max_by_income, max_by_dp))



# --- PROMINENT MAX BUYING POWER DISPLAY ---
st.markdown(f"""
<div style="background-color: {SLATE_ACCENT}; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px; border: 2px solid {PRIMARY_GOLD};">
    <p style="margin: 0; font-size: 1.1em; text-transform: uppercase; letter-spacing: 2px;">Maximum Qualified Buying Power</p>
    <h1 style="margin: 10px 0; font-size: 3.5em; color: {PRIMARY_GOLD};">${max_buying_power:,.0f}</h1>
    <p style="margin: 0; font-size: 0.95em; opacity: 0.9;">
        This limit is driven by the <b>Minimum</b> of two stress tests:
    </p>
    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 15px;">
        <div style="background: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 8px;">
            <span style="font-size: 0.8em; display: block;">DSCR/Income Test</span>
            <b>${max_by_income:,.0f}</b>
        </div>
        <div style="background: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 8px;">
            <span style="font-size: 0.8em; display: block;">20% Down Payment Rule</span>
            <b>${max_by_dp:,.0f}</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 6. CORE INPUTS ---
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("💰 Capital Requirement")
    store['down_payment'] = st.number_input("Available Down Payment ($)", value=float(store['down_payment']), step=5000.0)
    
    # User inputs purchase price within qualified range
    new_price = st.number_input("Purchase Price ($)", 
                                value=min(float(store['target_price']), max_buying_power), 
                                max_value=max_buying_power, step=5000.0)
    
    if new_price != store['target_price']:
        store['target_price'] = new_price
        store['annual_prop_tax'] = new_price * default_tax_rate
        if is_rental: store['manual_rent'] = (new_price * (scraped_yield/100)) / 12

    store['contract_rate'] = st.number_input("Mortgage Contract Rate (%)", value=float(store['contract_rate']), step=0.1)
    
    if is_rental:
        store['manual_rent'] = st.number_input("Monthly Projected Rent ($)", value=float(store['manual_rent']))
        st.caption(f"💡 {asset_province} Yield Guide: {scraped_yield}%")
        store['vacancy_months'] = st.number_input("Vacancy (no. of months. max 12 mo)", 0.0, 12.0, value=float(store['vacancy_months']))
    else:
        st.info(f"ℹ️ Secondary Home: Household income must support costs in {asset_province}.")

with c_right:
    st.subheader("🏙️ Carrying Costs")
    store['annual_prop_tax'] = st.number_input("Annual Property Tax ($)", value=float(store['annual_prop_tax']))
    store['strata_mo'] = st.number_input("Monthly Strata ($)", value=float(store['strata_mo']))
    store['insurance_mo'] = st.number_input("Monthly Insurance ($)", value=float(store['insurance_mo']))
    store['rm_mo'] = st.number_input("Repairs & Maintenance (Monthly)", value=float(store['rm_mo']))
    
    bc_extra_mo = 0
    if asset_province == "BC" and not is_rental:
        st.markdown("---")
        spec_tax = store['target_price'] * 0.005
        vanc_check = st.checkbox("Property in Vancouver?")
        vanc_empty_tax = store['target_price'] * 0.03 if vanc_check else 0
        st.warning(f"🌲 BC Specifics: Spec Tax: ${spec_tax:,.0f} | Empty Home Tax: ${vanc_empty_tax:,.0f}")
        bc_extra_mo = (spec_tax + vanc_empty_tax) / 12

    mgmt_fee = (store['manual_rent'] * (store['mgmt_pct'] / 100)) if is_rental else 0
    if is_rental: store['mgmt_pct'] = st.slider("Property Management Fee %", 0.0, 12.0, float(store['mgmt_pct']))
    
    total_opex_mo = (store['annual_prop_tax'] / 12) + store['strata_mo'] + store['insurance_mo'] + store['rm_mo'] + bc_extra_mo + mgmt_fee
    st.markdown(f"""<div style="background-color: {SLATE_ACCENT}; color: white; padding: 5px 15px; border-radius: 5px; text-align: center; margin-top: 10px;">
        Total Monthly OpEx: <b>${total_opex_mo:,.0f}</b></div>""", unsafe_allow_html=True)

# --- 7. ANALYSIS & TABLES ---
target_loan = max(0, store['target_price'] - store['down_payment'])
r_contract = (store['contract_rate'] / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0
realized_rent = (store['manual_rent'] * (12 - store['vacancy_months'])) / 12 if is_rental else 0
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

# --- 8. METRICS BAR ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
with m1:
    m_color = DARK_GREEN if asset_net >= 0 else CRIMSON_RED
    st.markdown(f"<b style='font-size: 0.85em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{m_color}; margin-top: 0;'>${asset_net:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)
with m2:
    coc = (asset_net * 12 / store['down_payment'] * 100) if store['down_payment'] > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Cash-on-Cash Return</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{coc:.1f}%</h3>", unsafe_allow_html=True)
with m3:
    st.markdown(f"<b style='font-size: 0.85em;'>Household Safety Margin</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{'#16a34a' if safety_margin > 10 else '#ca8a04'}; margin-top: 0;'>{safety_margin:.1f}%</h3>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<b style='font-size: 0.85em;'>Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}</h3>", unsafe_allow_html=True)

# --- 9. STRATEGIC VERDICT ---
st.subheader("🎯 Strategic Verdict")

is_neg_carry = is_rental and asset_net < 0
is_low_safety = not is_rental and safety_margin < 45
is_unsustainable = overall_cash_flow < 0

if is_unsustainable:
    v_status, v_color, v_bg = "❌ Unsustainable Move", "#dc2626", "#FEF2F2"
    v_msg = "Total monthly obligations exceed your current net income inflow."
elif is_neg_carry or is_low_safety:
    v_status, v_color, v_bg = "⚠️ Speculative Move", "#ca8a04", "#FFFBEB"
    v_msg = "This acquisition is viable on paper but carries significant lifestyle opportunity costs."
else:
    v_status, v_color, v_bg = "✅ Strategically Sound", "#16a34a", "#F0FDF4"
    v_msg = "Your household ecosystem shows strong resilience for this acquisition."

v_html = []
v_html.append(f"<div style='background-color: {v_bg}; padding: 20px; border-radius: 10px; border: 1.5px solid {v_color}; color: {SLATE_ACCENT};'>")
v_html.append(f"<h4 style='color: {v_color}; margin-top: 0;'>{v_status}</h4>")
v_html.append(f"<p style='font-size: 1.05em; line-height: 1.5; margin-bottom: 10px;'>{v_msg}</p>")
v_html.append("<div style='font-size: 1em;'>")
v_html.append(f"<p style='margin: 5px 0;'>• <b>The \"Blind Spot\" Warning:</b> The overall cash flow of <b>${overall_cash_flow:,.0f}</b> does not account for non-household expenses such as food, utilities, shopping, childcare, etc.</p>")

if is_neg_carry:
    v_html.append(f"<p style='margin: 5px 0;'>• <b>Negative Carry:</b> This rental requires <b>${abs(asset_net):,.0f}</b>/mo from your salary to stay afloat. This is a capital growth play, not a cash flow play.</p>")

if is_low_safety:
    v_html.append(f"<p style='margin: 5px 0;'>• <b>Leverage Alert:</b> Your Safety Margin is <b>{safety_margin:.1f}%</b>. Thresholds below 45% (pre-lifestyle) are considered high-leverage for secondary homes.</p>")

v_html.append("</div></div>")

st.markdown("".join(v_html), unsafe_allow_html=True)

# --- 10. ERROR & OMISSION DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption(f"Analyst in a Pocket | Portfolio Strategy | Asset Province: {asset_province}")
