import streamlit as st
import pandas as pd
import os
import json
import math

# --- 1. THEME & STYLING ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

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

# --- 2. DATA CROSS-REFERENCING ---
prof = st.session_state.get('user_profile', {})
current_residence = prof.get('province', 'BC')
p1_name = prof.get('p1_name', 'Client A')
p2_name = prof.get('p2_name', 'Client B')
household = f"{p1_name} & {p2_name}".strip(" & ")

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()

# --- 3. PROVINCE SELECTION (NEW) ---
st.subheader("📍 Asset Location")
prov_options = ["BC", "Alberta", "Ontario", "Manitoba", "Quebec", "Nova Scotia", "New Brunswick", "Saskatchewan"]
# Default to current residence province
asset_province = st.selectbox("Select the Province for the new property:", options=prov_options, index=prov_options.index(current_residence) if current_residence in prov_options else 0)

scraped_yield = intel.get("provincial_yields", {}).get(asset_province, 3.8)
tax_rate_lookup = {"BC": 0.0031, "Ontario": 0.0076, "Alberta": 0.0064}
default_tax_rate = tax_rate_lookup.get(asset_province, 0.0075)

# --- 4. PERSISTENCE ---
if "aff_second_store" not in st.session_state:
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "is_rental": True,
        "target_price": 600000.0,
        "manual_rent": 0.0,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "vacancy_months": 1.0
    }
store = st.session_state.aff_second_store

# --- 5. MATH ENGINE ---
p1_annual = float(prof.get('p1_t4', 0) + prof.get('p1_bonus', 0) + prof.get('p1_commission', 0))
p2_annual = float(prof.get('p2_t4', 0) + prof.get('p2_bonus', 0) + prof.get('p2_commission', 0))
total_income_annual = p1_annual + p2_annual + (float(prof.get('inv_rental_income', 0)) * 0.80)
m_inc = total_income_annual / 12

m_bal = float(prof.get('m_bal', 0))
m_rate_p = (float(prof.get('m_rate', 4.0)) / 100) / 12
primary_p_i = (m_bal * m_rate_p) / (1 - (1 + m_rate_p)**-300) if m_bal > 0 else 0
primary_carrying = (float(prof.get('prop_taxes', 4200)) / 12) + float(prof.get('heat_pmt', 125))
p_debts = float(prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0) + (float(prof.get('loc_balance', 0)) * 0.03))

# Qualifying Max
stress_rate = max(5.25, store.get('contract_rate', 4.26) + 2.0)
r_stress = (stress_rate / 100) / 12
stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)
rental_offset = (store.get('manual_rent', 0) * 0.80) if store.get('is_rental') else 0
qual_room = (m_inc * 0.44) + rental_offset - primary_p_i - primary_carrying - p_debts - (store['target_price'] * default_tax_rate / 12)
max_affordable = custom_round_up((qual_room / stress_k) + store['down_payment']) if qual_room > 0 else store['down_payment']

# --- 6. STORYTELLING HEADER ---
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 20px 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-top: 15px; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">🏢 Scenario Analysis: Secondary Home Acquisition</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.5; margin-bottom: 0;">
        Exploring capital deployment for a <b>Rental Asset</b> or <b>Family Residence</b> in {asset_province}. 
        We test the household ecosystem for long-term viability and cash-flow impact.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 7. INPUTS ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("📊 Capital & Use Case")
    store['is_rental'] = st.toggle("Rental Property Use Case", value=store.get('is_rental', True))
    store['down_payment'] = st.number_input("Down Payment Capital ($)", value=float(store['down_payment']), step=5000.0)
    store['target_price'] = st.number_input(f"Target Purchase Price (Max Qual: ${max_affordable:,.0f})", 
                                           value=min(float(store['target_price']), max_affordable), 
                                           max_value=max_affordable, step=5000.0)
    store['contract_rate'] = st.number_input("Mortgage Contract Rate (%)", value=float(store['contract_rate']), step=0.1)
    
    if store['is_rental']:
        auto_rent = (store['target_price'] * (scraped_yield/100)) / 12
        store['manual_rent'] = st.number_input("Monthly Projected Rent ($)", value=float(auto_rent))
        st.caption(f"💡 {asset_province} Yield Estimate: {scraped_yield}% based on current market data.")
        store['vacancy_months'] = st.number_input("Vacancy Months / Year", 0.0, 12.0, value=float(store['vacancy_months']))
    else:
        st.info(f"ℹ️ Secondary Home: Household income must support 100% of the carrying costs in {asset_province}.")

with c_right:
    st.subheader("🏙️ Carrying Costs")
    # Auto-calculate property tax based on province-specific rates
    calc_tax = store['target_price'] * default_tax_rate
    store['annual_prop_tax'] = st.number_input("Annual Property Tax ($)", value=float(calc_tax))
    store['strata_mo'] = st.number_input("Monthly Strata ($)", value=float(store['strata_mo']))
    store['insurance_mo'] = st.number_input("Monthly Insurance ($)", value=float(store['insurance_mo']))
    
    bc_extra_mo = 0
    if asset_province == "BC" and not store['is_rental']:
        st.markdown("---")
        # BC Speculation Tax (0.5% for citizens/residents)
        spec_tax = store['target_price'] * 0.005
        # Vancouver Empty Home Tax (3% if vacant > 6 months)
        vanc_empty_tax = store['target_price'] * 0.03 if st.checkbox("Property is within City of Vancouver?") else 0
        
        st.warning(f"🌲 BC Specifics: Est. Annual Speculation Tax: ${spec_tax:,.0f}")
        if vanc_empty_tax > 0:
            st.error(f"⚠️ Vancouver Empty Home Tax applied: ${vanc_empty_tax:,.0f}")
        bc_extra_mo = (spec_tax + vanc_empty_tax) / 12

# --- 8. CASH FLOW BREAKDOWN ---
target_loan = max(0, store['target_price'] - store['down_payment'])
r_contract = (store['contract_rate'] / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0

realized_rent = (store['manual_rent'] * (12 - store.get('vacancy_months', 1))) / 12 if store['is_rental'] else 0
total_asset_opex = (store['annual_prop_tax'] / 12) + store['strata_mo'] + store['insurance_mo'] + bc_extra_mo
asset_net = realized_rent - total_asset_opex - new_p_i

net_h_inc = (total_income_annual * 0.75) / 12 # Estimate
overall_cash_flow = (net_h_inc + realized_rent) - (primary_p_i + primary_carrying + p_debts + new_p_i + total_asset_opex)

st.subheader("📝 Monthly Cash Flow Breakdown")
c_in, c_out = st.columns(2)
with c_in:
    st.markdown("**Household Ecosystem**")
    st.table(pd.DataFrame([
        {"Item": "Net Household Income", "Amount": f"${net_h_inc:,.0f}"},
        {"Item": "Primary Home & Debts", "Amount": f"-${primary_p_i + primary_carrying + p_debts:,.0f}"},
        {"Item": "Monthly Surplus", "Amount": f"${net_h_inc - (primary_p_i + primary_carrying + p_debts):,.0f}"}
    ]))
with c_out:
    st.markdown("**Secondary Asset Impact**")
    st.table(pd.DataFrame([
        {"Item": "Realized Rent", "Amount": f"${realized_rent:,.0f}"},
        {"Item": "OpEx & New Mortgage", "Amount": f"-${total_asset_opex + new_p_i:,.0f}"},
        {"Item": "Net Asset Cash Flow", "Amount": f"${asset_net:,.0f}"}
    ]))

# --- 9. STRATEGY METRICS ---
st.divider()
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<b style='font-size: 0.85em;'>Asset Self-Sufficiency</b>", unsafe_allow_html=True)
    color = "#16a34a" if asset_net >= 0 else "#dc2626"
    st.markdown(f"<h3 style='color:{color}; margin-top: 0;'>${asset_net:,.0f}<small>/mo</small></h3>", unsafe_allow_html=True)
with m2:
    coc = (asset_net * 12 / store['down_payment'] * 100) if store['down_payment'] > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Cash-on-Cash Return</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{coc:.1f}%</h3>", unsafe_allow_html=True)
with m3:
    safety = (overall_cash_flow / (net_h_inc + realized_rent) * 100) if (net_h_inc + realized_rent) > 0 else 0
    st.markdown(f"<b style='font-size: 0.85em;'>Household Safety Margin</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>{safety:.1f}%</h3>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<b style='font-size: 0.85em;'>Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}</h3>", unsafe_allow_html=True)

st.caption(f"Analyst in a Pocket | Portfolio Strategy | Asset Province: {asset_province}")
