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

# --- 2. DATA RETRIEVAL (MAPPING TO YOUR JSON) ---
prof = st.session_state.get('user_profile', {})
province = prof.get('province', 'BC')
p1 = prof.get('p1_name', 'Client A')
p2 = prof.get('p2_name', 'Client B')
household = f"{p1} & {p2}".strip(" & ")

def load_market_intel():
    path = os.path.join("data", "market_intel.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"rates": {"five_year_fixed_uninsured": 4.26}, "provincial_yields": {"BC": 3.8}}

intel = load_market_intel()
scraped_yield = intel.get("provincial_yields", {}).get(province, 3.8)

# --- 3. PERSISTENCE ---
if "aff_second_store" not in st.session_state:
    st.session_state.aff_second_store = {
        "down_payment": 200000.0,
        "is_rental": True,
        "target_price": 500000.0,
        "manual_rent": 0.0,
        "contract_rate": float(intel.get('rates', {}).get('five_year_fixed_uninsured', 4.26)),
        "annual_prop_tax": 3500.0,
        "strata_mo": 400.0,
        "insurance_mo": 100.0,
        "vacancy_months": 1.0,
        "bc_spec_tax": 0.0,
        "vancouver_empty_tax": 0.0
    }
store = st.session_state.aff_second_store

# --- 4. CALCULATION ENGINE ---
# Income: T4 + Bonus + Commission
p1_income = prof.get('p1_t4', 0) + prof.get('p1_bonus', 0) + prof.get('p1_commission', 0)
p2_income = prof.get('p2_t4', 0) + prof.get('p2_bonus', 0) + prof.get('p2_commission', 0)
total_annual_qual = p1_income + p2_income + (prof.get('inv_rental_income', 0) * 0.80)
m_inc = total_annual_qual / 12

# Primary Liabilities
m_bal = prof.get('m_bal', 0)
m_rate_primary = (prof.get('m_rate', 4.0) / 100) / 12
primary_mtg_pmt = (m_bal * m_rate_primary) / (1 - (1 + m_rate_primary)**-300) if m_bal > 0 else 0
primary_carrying = (prof.get('prop_taxes', 4200) / 12) + prof.get('heat_pmt', 125)

# Personal Debts
personal_debts = prof.get('car_loan', 0) + prof.get('student_loan', 0) + prof.get('cc_pmt', 0) + (prof.get('loc_balance', 0) * 0.03)

# QUALIFYING MAX CALC
stress_rate = max(5.25, store['contract_rate'] + 2.0)
r_stress = (stress_rate / 100) / 12
stress_k = (r_stress * (1 + r_stress)**300) / ((1 + r_stress)**300 - 1)

rental_offset = (store['manual_rent'] * 0.80) if store['is_rental'] else 0
qual_room = (m_inc * 0.44) + rental_offset - primary_mtg_pmt - primary_carrying - personal_debts - (store['annual_prop_tax']/12)
max_loan = qual_room / stress_k if qual_room > 0 else 0
max_affordable = custom_round_up(max_loan + store['down_payment'])

# --- 5. UI & INPUTS ---
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Portfolio Expansion Map")

st.markdown(f"""<div style="background-color: {OFF_WHITE}; padding: 15px; border-radius: 10px; border-left: 8px solid {PRIMARY_GOLD};">
    <b>Scenario:</b> Secondary Acquisition for {household} in {province}.
</div>""", unsafe_allow_html=True)

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏠 Purchase Plan")
    store['is_rental'] = st.toggle("Rental Property Use Case", value=store['is_rental'])
    store['down_payment'] = st.number_input("Down Payment ($)", value=float(store['down_payment']), step=5000.0)
    
    # Target Price Input (Capped by Max)
    store['target_price'] = st.number_input(f"Target Purchase Price (Max: ${max_affordable:,.0f})", 
                                           value=min(float(store['target_price']), max_affordable), 
                                           max_value=max_affordable, step=5000.0)
    
    store['contract_rate'] = st.number_input("Mortgage Rate (%)", value=float(store['contract_rate']), step=0.1)
    
    if store['is_rental']:
        if store['manual_rent'] == 0: store['manual_rent'] = (store['target_price'] * (scraped_yield/100)) / 12
        store['manual_rent'] = st.number_input("Monthly Rent ($)", value=float(store['manual_rent']))
        store['vacancy_months'] = st.number_input("Vacancy Months / Year", 0.0, 12.0, value=float(store['vacancy_months']))

with col_right:
    st.subheader("📑 Carrying Costs")
    store['annual_prop_tax'] = st.number_input("Annual Property Tax ($)", value=float(store['annual_prop_tax']))
    store['strata_mo'] = st.number_input("Monthly Strata ($)", value=float(store['strata_mo']))
    store['insurance_mo'] = st.number_input("Monthly Insurance ($)", value=float(store['insurance_mo']))
    
    bc_extra = 0
    if province == "BC":
        with st.expander("🌲 BC Vacancy/Empty Home Taxes"):
            store['bc_spec_tax'] = st.number_input("Speculation & Vacancy Tax", value=float(store['bc_spec_tax']))
            store['vancouver_empty_tax'] = st.number_input("Vancouver Empty Homes Tax", value=float(store['vancouver_empty_tax']))
            bc_extra = (store['bc_spec_tax'] + store['vancouver_empty_tax']) / 12

# --- 6. FINAL CALCULATIONS ---
target_loan = max(0, store['target_price'] - store['down_payment'])
r_contract = (store['contract_rate'] / 100) / 12
new_p_i = (target_loan * r_contract) / (1 - (1 + r_contract)**-300) if target_loan > 0 else 0

realized_rent = (store['manual_rent'] * (12 - store['vacancy_months'])) / 12 if store['is_rental'] else 0
total_opex = (store['annual_prop_tax'] / 12) + store['strata_mo'] + store['insurance_mo'] + bc_extra
asset_net = realized_rent - total_opex - new_p_i

# Overall Household Surplus (Net Income Approx 75% of Gross)
net_h_inc = (total_annual_qual * 0.75) / 12
overall_cash_flow = (net_h_inc + realized_rent) - (primary_mtg_pmt + primary_carrying + personal_debts + new_p_i + total_opex)

# --- 7. METRICS ROW ---
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
    st.markdown(f"<b style='font-size: 0.85em;'>Monthly Overall Cash Flow</b>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0;'>${overall_cash_flow:,.0f}</h3>", unsafe_allow_html=True)

# --- 8. SUMMARY STATS ---
st.divider()
s1, s2, s3 = st.columns(3)
s1.metric("Target Acquisition", f"${store['target_price']:,.0f}")
s2.metric("Qualified Max", f"${max_affordable:,.0f}")
s3.metric("New Mtg Payment (P&I)", f"${new_p_i:,.0f}")

st.caption("Analyst in a Pocket | Portfolio Expansion & Secondary Home Strategy")
